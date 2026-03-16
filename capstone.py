import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="COVID-19 Country Tracker",
    page_icon="🦠",
    layout="wide",
)

CONFIRMED_URL = (
    "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/"
    "csse_covid_19_data/csse_covid_19_time_series/"
    "time_series_covid19_confirmed_global.csv"
)

DEATHS_URL = (
    "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/"
    "csse_covid_19_data/csse_covid_19_time_series/"
    "time_series_covid19_deaths_global.csv"
)

DEFAULT_COUNTRIES = ["US", "India", "Brazil"]


@st.cache_data(show_spinner=False)
def load_metric_timeseries(csv_url: str) -> pd.DataFrame:
    df = pd.read_csv(csv_url)
    date_cols = df.columns[4:]
    country_ts = df.groupby("Country/Region")[date_cols].sum().T
    country_ts.index = pd.to_datetime(country_ts.index)
    country_ts = country_ts.sort_index()
    country_ts.index.name = "Date"
    return country_ts


@st.cache_data(show_spinner=False)
def load_all_data() -> dict[str, pd.DataFrame]:
    confirmed = load_metric_timeseries(CONFIRMED_URL)
    deaths = load_metric_timeseries(DEATHS_URL)
    return {"Cases": confirmed, "Deaths": deaths}


@st.cache_data(show_spinner=False)
def build_download_table(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out.index = out.index.strftime("%Y-%m-%d")
    out.index.name = "Date"
    return out.reset_index()


def get_display_frame(base_df: pd.DataFrame, mode: str) -> pd.DataFrame:
    if mode == "Daily":
        daily = base_df.diff().fillna(0).clip(lower=0)
        return daily.astype(int)
    return base_df.astype(int)


st.title("COVID-19 Country Tracker")
st.caption(
    "Interactive web app using the Johns Hopkins CSSE global time-series dataset. "
    "The repository is archived, so the historical data ends in March 2023."
)

with st.spinner("Loading data..."):
    metric_data = load_all_data()

available_countries = sorted(metric_data["Cases"].columns.tolist())

with st.sidebar:
    st.header("Controls")

    selected_metric = st.radio("Metric", ["Cases", "Deaths"], horizontal=True)
    selected_mode = st.radio("Display mode", ["Cumulative", "Daily"], horizontal=True)

    selected_countries = st.multiselect(
        "Choose one or more countries",
        options=available_countries,
        default=[c for c in DEFAULT_COUNTRIES if c in available_countries],
    )

    base_df = metric_data[selected_metric]
    min_date = base_df.index.min().date()
    max_date = base_df.index.max().date()

    selected_dates = st.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    st.markdown("---")
    st.info(
        "Tip: choose **Daily** to see day-by-day changes, or **Cumulative** to see total counts."
    )

if not selected_countries:
    st.warning("Please select at least one country.")
    st.stop()

if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date = min_date
    end_date = max_date

base_df = metric_data[selected_metric][selected_countries]
display_df = get_display_frame(base_df, selected_mode)
filtered_df = display_df.loc[str(start_date):str(end_date)]

if filtered_df.empty:
    st.warning("No data available for the selected date range.")
    st.stop()

latest_date = filtered_df.index.max()
latest_values = filtered_df.loc[latest_date].sort_values(ascending=False)

st.markdown(
    f"**Data window:** {filtered_df.index.min().date()} to {filtered_df.index.max().date()}  "
    f"| **Latest date shown:** {latest_date.date()}"
)

st.subheader(f"Latest {selected_mode.lower()} {selected_metric.lower()} by country")
metric_cols = st.columns(min(4, len(selected_countries)))
for i, (country, value) in enumerate(latest_values.items()):
    metric_cols[i % len(metric_cols)].metric(country, f"{int(value):,}")

st.subheader(f"Trend chart: {selected_mode} {selected_metric}")
chart_df = filtered_df.copy()
chart_df.index = pd.to_datetime(chart_df.index)
st.line_chart(chart_df)

col1, col2 = st.columns([1.1, 0.9])

with col1:
    st.subheader("Latest values table")
    latest_table = latest_values.rename("Value").reset_index()
    latest_table.columns = ["Country", "Value"]
    latest_table["Value"] = latest_table["Value"].map(lambda x: f"{int(x):,}")
    st.dataframe(latest_table, width="stretch", hide_index=True)

with col2:
    st.subheader("Download selected data")
    download_df = build_download_table(filtered_df)
    csv_bytes = download_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download CSV",
        data=csv_bytes,
        file_name=f"covid_{selected_metric.lower()}_{selected_mode.lower()}.csv",
        mime="text/csv",
        width="stretch",
    )
    st.dataframe(download_df.tail(10), width="stretch", hide_index=True)

with st.expander("About this app"):
    st.write(
        "This app aggregates province/state rows to the country level, lets the user compare "
        "multiple countries, and switches between daily and cumulative views."
    )
    st.write(
        "Because the Johns Hopkins CSSE repository was archived in March 2023, this app is a "
        "historical tracker rather than a live COVID dashboard."
    )