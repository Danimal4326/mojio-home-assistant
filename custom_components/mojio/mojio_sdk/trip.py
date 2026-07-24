from .abstract_mojio import AbstractMojio
from .polyline import METERS_PER_MILE, path_distance_meters


class Trip(AbstractMojio):

    def __init__(self, json_data):
        super().__init__(json_data)
        if not self.has_data:
            return
        self.id = json_data.get('Id', '')
        self.vehicle_id = json_data.get('VehicleId', '')
        self.start_date = json_data.get('StartTimestamp', '')
        self.end_date = json_data.get('EndTimestamp', '')
        self.completed = json_data.get('Completed', False)
        temp_duration = json_data.get('Duration', None)
        if temp_duration is not None and self.completed:
            # Truncate off the microsections, because who cares.
            s = temp_duration.split('.')
            if len(s) > 0:
                self.duration = s[0]
        # Speed and RPM
        max_rpm_dict = json_data.get('MaxRPM', None)
        if max_rpm_dict is not None:
            self.max_rpm = max_rpm_dict.get('Value', 0)
            self.max_rpm_unit = max_rpm_dict.get('Unit', '')
        # Max Speed
        max_speed_dict = json_data.get('MaxSpeed', None)
        if max_speed_dict is not None:
            self.max_speed_unit = max_speed_dict.get('Unit', '')
            if 'kilometers' in self.max_speed_unit.lower():
                self.max_speed_kph = max_speed_dict.get('Value', 0)
                self.max_speed_mph = float(self.max_speed_kph) / 1.609
            else:
                self.max_speed_mph = max_speed_dict.get('Value', 0)
                self.max_speed_kph = float(self.max_speed_mph) * 1.609
        # Harsh Accel
        self.harsh_accel = 0
        if self.completed and json_data.get('HarshAcclCount') is not None:
            self.harsh_accel = json_data.get('HarshAcclCount', 0)

        # Fuel
        fuel_effic_dict = json_data.get('FuelEfficiency', None)
        if self.completed and fuel_effic_dict is not None:
            self.fuel_efficiency_unit = fuel_effic_dict.get('Unit', '')
            if 'kilometer' in self.fuel_efficiency_unit.lower():
                self.kpl = fuel_effic_dict.get('Value', 0)
                self.mpg = float(self.kpl) * 2.352145
            else:
                self.mgp = fuel_effic_dict.get('Value', 0)
                self.kpl = float(self.mgp) / 2.352145

        # Distance
        self.distance_is_derived = False
        distance_dict = json_data.get('Distance', None)
        if self.completed and distance_dict is not None:
            self.distance_unit = distance_dict.get('Unit', '')
            distance = distance_dict.get('Value', 0)
            if 'Meters' == self.distance_unit:
                self.distance_km = distance / 1000
                self.distance_mi = distance / 1609
            elif 'kilo' in self.distance_unit.lower():
                self.distance_km = distance
                self.distance_mi = distance / 1.609
            else:
                self.distance_km = distance * 1.609
                self.distance_mi = distance

        # Some tenants (e.g. Audi) report a flat 0 distance on every trip while
        # still returning the GPS path, so recover the distance from the
        # polyline. Flagged as derived since it's a GPS-sampled approximation
        # and reads slightly short of a true odometer.
        if self.completed and not self.getattribute('distance_km', 0):
            derived_meters = path_distance_meters(json_data.get('Polyline'))
            if derived_meters > 0:
                self.distance_unit = 'Meters'
                self.distance_km = derived_meters / 1000
                self.distance_mi = derived_meters / METERS_PER_MILE
                self.distance_is_derived = True

    @staticmethod
    def get_trip(trips: list, trip_id: str):
        '''Returns the specifed trip_id'''
        return [trip for trip in trips if trip.id == trip_id]

    @staticmethod
    def get_trips(trips: list, vehicle_id, completed_only=None):
        '''Returns a list of Trips for a vehicle.

        vehicle_id is normally Vehicle.mojio_id, but may also be an iterable of
        candidate ids for tenants that expose more than one id per vehicle.
        '''
        candidate_ids = Trip._as_id_set(vehicle_id)
        if completed_only is None:
            return [trip for trip in trips if trip.vehicle_id in candidate_ids]
        else:
            return [trip for trip in trips
                    if trip.vehicle_id in candidate_ids and trip.completed is completed_only]

    @staticmethod
    def get_last_trip(trips: list, vehicle_id, completed_only=False):
        '''Returns the last trip for a vehicle'''
        candidate_ids = Trip._as_id_set(vehicle_id)
        last_trip = Trip({})
        for trip in trips:
            if trip.vehicle_id in candidate_ids and trip.completed is completed_only:
                last_trip = trip
                break
        return last_trip

    @staticmethod
    def _as_id_set(vehicle_id):
        if isinstance(vehicle_id, str):
            return {vehicle_id}
        return {vid for vid in vehicle_id if vid}
