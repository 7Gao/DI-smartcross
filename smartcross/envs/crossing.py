import traci
import numpy as np


class Crossing:

    def __init__(self, tls_id, env, tcnn):
        self._id = tls_id
        self._env = env
        self._incoming_lanes = list(set(traci.trafficlight.getControlledLanes(self._id)))
        self._outgoing_lanes = list(set([l[0][1] for l in traci.trafficlight.getControlledLinks(self._id)]))
        self._lane_length = {l: traci.lane.getLength(l) for l in self._incoming_lanes}

        self._lane_vehicle_dict = {}
        self._vehicle_lane_dict = {}
        signal_definition = traci.trafficlight.getCompleteRedYellowGreenDefinition(self._id)[0]
        self._green_phases = []
        self._yellow_phases = []
        for idx, phase in enumerate(signal_definition.phases):
            if phase.state.count('G') > 1:
                self._green_phases.append(idx)
            elif phase.state.count('y') > 1:
                self._yellow_phases.append(idx)
        assert len(self._green_phases) == len(self._green_phases) > 0

    def _update_measurement(self):
        raw_phase = traci.trafficlight.getPhase(self._id)
        if raw_phase in self._green_phases:
            self._current_phase = self._green_phases.index(raw_phase)
        elif raw_phase in self._yellow_phases:
            self._current_phase = self._yellow_phases.index(raw_phase)
        else:
            self._current_phase = -1
        self._current_phase_duration = traci.trafficlight.getPhaseDuration(self._id)

    def _update_lane_vehicle_info(self):
        for lane in self._incoming_lanes + self._outgoing_lanes:
            self._lane_vehicle_dict[lane] = traci.lane.getLastStepVehicleIDs(lane)
            for veh in self._lane_vehicle_dict[lane]:
                if veh not in self._env.vehicle_info:
                    self._env.vehicle_info[veh] = {}

    def update_timestep(self):
        self._update_measurement()
        self._update_lane_vehicle_info()
    
    def set_phase(self, phase_id, duration):
        traci.trafficlight.setPhase(self._id, phase_id)
        traci.trafficlight.setPhaseDuration(self._id, duration)

    def get_onehot_phase(self):
        onehot = [0] * len(self._green_phases)
        onehot[self._current_phase] = 1
        return onehot

    def get_green_phase_index(self, idx):
        return self._green_phases[idx]

    def get_yellow_phase_index(self, idx):
        return self._yellow_phases[idx]

    def get_lane_vehicle_pos_vector(self, grid_num):
        vehicle_pos_vector = {}
        for lane in self._incoming_lanes:
            lane_vec = [0] * grid_num
            for veh in self._lane_vehicle_dict[lane]:
                lane_pos = traci.vehicle.getLanePosition(veh)
                lane_len = self._lane_length[lane]
                tl_dist = lane_len - lane_pos
                pos_idx = int((tl_dist / lane_len) * grid_num)
                pos_idx = np.clip(pos_idx, 0, grid_num - 1)
                lane_vec[pos_idx] = 1
            vehicle_pos_vector[lane] = lane_vec
        return vehicle_pos_vector
    
    def get_lane_traffic_volumn(self, volumn_ratio):
        traffic_volumn_dict = {}
        for lane in self._incoming_lanes:
            veh_num = traci.lane.getLastStepVehicleNumber(lane)
            traffic_volumn = veh_num / (self._lane_length[lane] / volumn_ratio)
            traffic_volumn_dict[lane] = traffic_volumn
        return traffic_volumn_dict
    
    def get_lane_occupancy(self):
        occupancy_dict = {}
        for lane in self._incoming_lanes:
            occupancy = traci.lane.getLastStepOccupancy(lane)
            occupancy_dict[lane] = occupancy
        return occupancy_dict
    
    def get_lane_queue_len(self, len_ratio=None):
        queue_len_dict = {}
        for lane in self._incoming_lanes:
            queue_len = traci.lane.getLastStepHaltingNumber(lane)
            if len_ratio is not None:
                queue_len /= (self._lane_length[lane] / len_ratio)
            queue_len_dict[lane] = queue_len
        return queue_len_dict

    def get_lane_wait_time(self):
        wait_time_dict = {}
        for lane in self._incoming_lanes:
            wait_time = 0
            for veh in self._lane_vehicle_dict[lane]:
                cur_wait_time = traci.vehicle.getAccumulatedWaitingTime(veh)
                if 'wait_time' not in self._env.vehicle_info[veh]:
                    self._env.vehicle_info[veh]['wait_time'] = 0
                wait_time += cur_wait_time - self._env.vehicle_info[veh]['wait_time']
                self._env.vehicle_info[veh]['wait_time'] = cur_wait_time
            wait_time_dict[lane] = wait_time
        return wait_time_dict
    
    def get_lane_delay_time(self):
        delay_time_dict = {}
        for lane in self._incoming_lanes + self._outgoing_lanes:
            delay_time = 0
            for veh in self._lane_vehicle_dict[lane]:
                cur_distace = traci.vehicle.getDistance(veh)
                cur_time = traci.vehicle.getLastActionTime(veh)
                if 'distance' not in self._env.vehicle_info[veh]:
                    self._env.vehicle_info[veh]['distance'] = cur_distace
                    self._env.vehicle_info[veh]['time'] = cur_time
                else:
                    real_distance = cur_distace - self._env.vehicle_info[veh]['distance']
                    target_speed = traci.vehicle.getMaxSpeed(veh)
                    target_distance = (cur_time - self._env.vehicle_info[veh]['time']) * target_speed
                    delay_time += (target_distance - real_distance) / (target_speed + 1e-8)
            delay_time_dict[lane] = delay_time
        return delay_time_dict

    def get_pressure(self):
        pressure = 0
        for lane in self._incoming_lanes:
            pressure += traci.lane.getLastStepVehicleNumber(lane)
        for lane in self._outgoing_lanes:
            pressure -= traci.lane.getLastStepVehicleNumber(lane)
        return abs(pressure)
    
    @property
    def current_phase(self):
        return self._current_phase, self._current_phase_duration
    
    @property
    def phase_num(self):
        return len(self._green_phases)
    
    @property
    def lane_num(self):
        return len(self._incoming_lanes)