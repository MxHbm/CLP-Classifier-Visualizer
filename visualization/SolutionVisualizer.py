import streamlit as st

import numpy as np
import pandas as pd

import seaborn as sns
import colorcet as cc

import json

from RouteVisualizer import make_routing_figure
from PackingVisualizer import make_packing_figure
from ColorConversion import hex_color_to_shaded_list


def main():
    st.set_page_config(layout="wide")

    st.title("Solution visualization of CLP classifier")

    show_solution()


def show_solution():
    uploaded_sol_file = st.sidebar.file_uploader("Please select a .json solution file", type="json")
    if uploaded_sol_file is not None:
        try:
            (
                loading_variant,
                costs,
                number_vehicles,
                tours,
                packings,
            ) = get_solution_data_from_json(uploaded_sol_file.getvalue())

        except KeyError as e:
            st.write(
                f"KeyError: {e} occurred while accessing JSON data. Please check again if you have uploaded a valid solution file."
            )
            return
        except Exception as e:
            st.write(f"An error occurred: {e}. Please check again if you have uploaded a valid solution file.")
            return

        st.sidebar.subheader("Solution statistics")
        st.sidebar.write(f"Loading problem variant: {loading_variant}")

        st.sidebar.write(f"Costs: {costs:.2f}")

        st.sidebar.write(f"Used vehicles: {number_vehicles}")

        st.header("Solution visualization")
        col1, col2 = st.columns(2)
        filter_mask = create_filter_mask(tours)

        with col1:
            st.subheader("Routing")
            filtered_tours = tours[filter_mask]

            fig = make_routing_figure(filtered_tours)

            config = dict({"scrollZoom": True})
            st.plotly_chart(fig, config=config, use_container_width=True)

            table_expander = st.expander("Detailed info on routes")
            with table_expander:
                st.subheader("Selected tours")
                st.table(filtered_tours.drop(["color", "sites"], axis=1))
                st.subheader("Remaining tours")
                st.table(tours[~filter_mask].drop(["color", "sites"], axis=1))

        with col2:
            st.subheader("Loading")

            selected_tours = [id for id in range(len(filter_mask)) if filter_mask[id] == 1]
            selected_tour_ids = st.multiselect("Visualize loading of tours", selected_tours)

            for packing in packings:
                fig = make_packing_figure(packing, selected_tour_ids)

                if fig is None:
                    continue

                st.plotly_chart(fig, use_container_width=True)



def create_filter_mask(tours):
    selected_tour_id = st.sidebar.multiselect("Select tour id", tours["tourId"])
    selected_tour_id_sites = st.sidebar.multiselect("Select sites", tours["sites"].explode().unique())

    filter_mask = np.ones((len(tours.index)), dtype=bool)

    if len(selected_tour_id_sites):
        filter_mask = filter_mask & (tours.sites.apply(lambda x: any([a in x for a in selected_tour_id_sites])))

    if len(selected_tour_id):
        filter_mask = filter_mask & tours.tourId.isin(selected_tour_id)

    return filter_mask


@st.cache_data
def get_solution_data_from_json(file):
    solution = json.loads(file)

    loading_variant = solution["ProblemVariant"]
    costs = solution["Solution"]["Costs"]
    number_vehicles = solution["Solution"]["NumberRoutes"]

    tours = get_tours_as_data_frame(solution["Solution"])
    packings = get_packings_as_data_frame(solution["Solution"], tours)

    return loading_variant, costs, number_vehicles, tours, packings


def get_packings_as_data_frame(solution, tours):
    new_tours = []
    for id, input_tour in enumerate(solution["Tours"]):
        tour = {}
        tour["TourId"] = id

        container = {}
        container["Dx"] = input_tour["Vehicle"]["Containers"][0]["Dx"]
        container["Dy"] = input_tour["Vehicle"]["Containers"][0]["Dy"]
        container["Dz"] = input_tour["Vehicle"]["Containers"][0]["Dz"]

        rgb_color = list(tours[tours.tourId == id].color)[0]
        container["Color"] = rgb_color

        tour["Container"] = container

        number_of_stops = len(input_tour["Route"])
        palette = hex_color_to_shaded_list(rgb_color, number_of_stops)

        sites = getattr(tours[tours.tourId == id], "sites").values[0]

        stops = []
        for stop_count, input_stop in enumerate(input_tour["Route"]):
            stop = {}
            stop["GroupId"] = number_of_stops - stop_count - 1

            new_items = []
            site_id = sites[stop_count]
            for input_item in input_stop["Items"]:
                item = {}
                item["Color"] = palette[stop_count]

                item["X"] = input_item["X"]
                item["Y"] = input_item["Y"]
                item["Z"] = input_item["Z"]

                item["EnableHorizontalRotation"] = input_item["EnableHorizontalRotation"]
                item["Rotated"] = input_item["Rotated"]
                item["Fragility"] = input_item["Fragility"]

                item["Dx"] = input_item["Dx"]
                item["Dy"] = input_item["Dy"]
                item["Dz"] = input_item["Dz"]

                item["SiteId"] = site_id

                new_items.append(item)

            stop["Items"] = new_items

            stops.append(stop)

        tour["Stops"] = stops
        new_tours.append(tour)

    return new_tours


def get_tours_as_data_frame(solution):
    depot_latitude = solution["Tours"][0]["Depot"]["Latitude"]
    depot_longitude = solution["Tours"][0]["Depot"]["Longitude"]

    number_of_routes = len(solution["Tours"])

    palette = sns.color_palette(cc.glasbey, n_colors=number_of_routes).as_hex()

    route_counter = 0
    tours = []
    for id, tour in enumerate(solution["Tours"]):
        if route_counter < 100:
            stops = []
            sites = []

            stops.append([depot_longitude, depot_latitude])
            for stop in tour["Route"]:
                lon = stop["Longitude"]
                lat = stop["Latitude"]

                stop_coordinates = [lon, lat]
                stops.append(stop_coordinates)
                sites.append(stop["InternId"])

            tour_id = id

            complete_route = []
            complete_route = stops

            new_tour = {}
            new_tour["tourId"] = tour_id
            new_tour["sites"] = sites
            new_tour["stops"] = "->".join([str(i) for i in sites])
            new_tour["coordinates"] = complete_route
            new_tour["color"] = palette[route_counter]

            tours.append(new_tour)
            route_counter += 1

    new_tours = pd.DataFrame(tours)

    return new_tours


if __name__ == "__main__":
    main()
