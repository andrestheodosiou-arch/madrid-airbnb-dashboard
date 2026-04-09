import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="ICB", layout="wide")

st.title("ICB")
st.markdown("**Madrid Airbnb Dashboard**")


@st.cache_data
def load_data():
    file_path = Path(__file__).parent / "airbnb.csv"

    if not file_path.exists():
        raise FileNotFoundError(
            f"Could not find airbnb.csv in: {file_path.parent}"
        )

    df = pd.read_csv(file_path, sep=",", skipinitialspace=True)
    df.columns = [c.strip().rstrip(";") for c in df.columns]

    required_cols = [
        "name",
        "room_type",
        "neighbourhood",
        "neighbourhood_group",
        "price",
        "reviews_per_month",
        "minimum_nights",
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    df = df.dropna(subset=["room_type", "neighbourhood", "neighbourhood_group"])

    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["reviews_per_month"] = pd.to_numeric(df["reviews_per_month"], errors="coerce")
    df["minimum_nights"] = pd.to_numeric(df["minimum_nights"], errors="coerce")

    df = df.dropna(subset=["price", "minimum_nights"])
    df = df[df["price"] > 0]
    df = df[df["price"] < 1000]

    return df


try:
    df = load_data()
except Exception as e:
    st.error(f"Failed to load dataset: {e}")
    st.stop()

st.success(f"Dataset loaded successfully: {df.shape[0]} rows, {df.shape[1]} columns")

neighbourhood_groups = sorted(df["neighbourhood_group"].dropna().unique().tolist())
room_types = sorted(df["room_type"].dropna().unique().tolist())

with st.sidebar:
    st.header("Filters")

    selected_groups = st.multiselect(
        "District",
        options=neighbourhood_groups,
        default=[]
    )

    selected_room_types = st.multiselect(
        "Room Type",
        options=room_types,
        default=[]
    )

    price_range = st.slider(
        "Price Range (€/night)",
        min_value=int(df["price"].min()),
        max_value=int(df["price"].max()),
        value=(int(df["price"].min()), int(df["price"].quantile(0.95)))
    )

filtered_df = df.copy()

if selected_groups:
    filtered_df = filtered_df[filtered_df["neighbourhood_group"].isin(selected_groups)]

if selected_room_types:
    filtered_df = filtered_df[filtered_df["room_type"].isin(selected_room_types)]

filtered_df = filtered_df[
    (filtered_df["price"] >= price_range[0]) &
    (filtered_df["price"] <= price_range[1])
]

if filtered_df.empty:
    st.warning("No data matches the selected filters. Try changing the sidebar filters.")
    st.stop()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Listings", f"{len(filtered_df):,}")
with col2:
    avg_price = filtered_df["price"].mean()
    st.metric("Avg Price (€/night)", f"€{avg_price:.0f}")
with col3:
    avg_reviews = filtered_df["reviews_per_month"].mean()
    if pd.isna(avg_reviews):
        st.metric("Avg Reviews / Month", "N/A")
    else:
        st.metric("Avg Reviews / Month", f"{avg_reviews:.2f}")

tab1, tab2 = st.tabs(["Listing Analysis", "Reviews & Pricing"])

with tab1:
    st.subheader("Room Type vs. Group Size Proxy")

    col_a, col_b = st.columns(2)

    with col_a:
        room_proxy_df = filtered_df.dropna(subset=["room_type", "minimum_nights"])
        room_proxy_df = room_proxy_df[room_proxy_df["minimum_nights"] <= 30]

        if room_proxy_df.empty:
            st.info("Not enough data to display Minimum Nights by Room Type.")
        else:
            fig_room = px.box(
                room_proxy_df,
                x="room_type",
                y="minimum_nights",
                color="room_type",
                title="Minimum Nights by Room Type (Proxy for Group Size)",
                labels={
                    "room_type": "Room Type",
                    "minimum_nights": "Minimum Nights"
                },
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_room.update_layout(showlegend=False)
            st.plotly_chart(fig_room, use_container_width=True)

    with col_b:
        price_type_df = filtered_df.dropna(subset=["room_type", "price"])

        if price_type_df.empty:
            st.info("Not enough data to display Price Distribution by Room Type.")
        else:
            fig_price_type = px.box(
                price_type_df,
                x="room_type",
                y="price",
                color="room_type",
                title="Price Distribution by Room Type",
                labels={
                    "room_type": "Room Type",
                    "price": "Price (€/night)"
                },
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_price_type.update_layout(showlegend=False)
            st.plotly_chart(fig_price_type, use_container_width=True)

    st.subheader("Listings by Neighbourhood")

    top_n = st.selectbox(
        "Show top N neighbourhoods",
        options=[10, 15, 20, 30],
        index=0
    )

    neigh_counts = (
        filtered_df["neighbourhood"]
        .dropna()
        .value_counts()
        .head(top_n)
        .reset_index()
    )
    neigh_counts.columns = ["neighbourhood", "count"]

    if neigh_counts.empty:
        st.info("Not enough data to display neighbourhood listing counts.")
    else:
        fig_neigh = px.bar(
            neigh_counts,
            x="count",
            y="neighbourhood",
            orientation="h",
            title=f"Top {top_n} Neighbourhoods by Number of Listings",
            labels={
                "count": "Number of Listings",
                "neighbourhood": "Neighbourhood"
            },
            color="count",
            color_continuous_scale="Blues"
        )
        fig_neigh.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_neigh, use_container_width=True)

    with st.expander("View Raw Data"):
        raw_cols = [
            "name",
            "neighbourhood",
            "neighbourhood_group",
            "room_type",
            "price",
            "reviews_per_month",
            "minimum_nights"
        ]
        existing_raw_cols = [col for col in raw_cols if col in filtered_df.columns]
        st.dataframe(filtered_df[existing_raw_cols].head(200), use_container_width=True)

with tab2:
    st.subheader("Relationship Between Number of Reviews and Price")

    scatter_df = filtered_df.dropna(subset=["reviews_per_month", "price", "room_type"])
    scatter_df = scatter_df[scatter_df["reviews_per_month"] < 20]

    if scatter_df.empty:
        st.info("Not enough data to display Price vs. Reviews per Month.")
    else:
        fig_scatter = px.scatter(
            scatter_df,
            x="price",
            y="reviews_per_month",
            color="room_type",
            title="Price vs. Reviews per Month",
            labels={
                "price": "Price (€/night)",
                "reviews_per_month": "Reviews per Month"
            },
            opacity=0.45,
            color_discrete_sequence=px.colors.qualitative.Set1
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    st.subheader("Neighbourhood Deep Dive")

    col_c, col_d = st.columns(2)

    with col_c:
        top_reviewed = (
            filtered_df.groupby("neighbourhood")["reviews_per_month"]
            .mean()
            .dropna()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        top_reviewed.columns = ["neighbourhood", "avg_reviews_per_month"]

        if top_reviewed.empty:
            st.info("Not enough data to display top reviewed neighbourhoods.")
        else:
            fig_top_rev = px.bar(
                top_reviewed,
                x="avg_reviews_per_month",
                y="neighbourhood",
                orientation="h",
                title="Top 10 Neighbourhoods by Avg Reviews / Month",
                labels={
                    "avg_reviews_per_month": "Avg Reviews / Month",
                    "neighbourhood": "Neighbourhood"
                },
                color="avg_reviews_per_month",
                color_continuous_scale="Oranges"
            )
            fig_top_rev.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_top_rev, use_container_width=True)

    with col_d:
        avg_price_neigh = (
            filtered_df.groupby("neighbourhood")["price"]
            .mean()
            .dropna()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        avg_price_neigh.columns = ["neighbourhood", "avg_price"]

        if avg_price_neigh.empty:
            st.info("Not enough data to display most expensive neighbourhoods.")
        else:
            fig_price_neigh = px.bar(
                avg_price_neigh,
                x="avg_price",
                y="neighbourhood",
                orientation="h",
                title="Top 10 Most Expensive Neighbourhoods",
                labels={
                    "avg_price": "Avg Price (€/night)",
                    "neighbourhood": "Neighbourhood"
                },
                color="avg_price",
                color_continuous_scale="Reds"
            )
            fig_price_neigh.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_price_neigh, use_container_width=True)