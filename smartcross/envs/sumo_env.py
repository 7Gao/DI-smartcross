import os
import sys
import time
from typing import Dict, Any, List, Tuple, Union
import numpy as np

import traci
from sumolib import checkBinary

from ding.envs import BaseEnv, BaseEnvTimestep, BaseEnvInfo
from ding.utils import ENV_REGISTRY
from ding.torch_utils import to_ndarray, to_tensor
from smartcross.envs.crossing import Crossing
from smartcross.envs.obs import SumoObsRunner
from smartcross.envs.action import SumoActionRunner
from smartcross.envs.reward import SumoRewardRunner
from smartcross.utils.config_utils import set_route_flow


@ENV_REGISTRY.register('sumo_env')
class SumoEnv(BaseEnv):

    def __init__(self, cfg: Dict) -> None:
        self._cfg = cfg
        self._sumocfg_path = os.path.dirname(__file__) + '/' + cfg.sumocfg_path
        self._gui = cfg.get('gui', False)
        self._dynamic_flow = cfg.get('dynamic_flow', False)
        if self._dynamic_flow:
            self._flow_range = cfg.flow_range
        self._tls = cfg.tls
        self._max_episode_steps = cfg.max_episode_steps
        self._yellow_duration = cfg.yellow_duration
        self._green_duration = cfg.green_duration

        self._launch_env_flag = False
        self._crosses = {}
        self._vehicle_info_dict = {}
        self._label = str(int(time.time() * (10 ** 6)))[-6:]

        self._launch_env(False)
        for tl in self._cfg.tls:
            self._crosses[tl] = Crossing(tl, self)
        self._obs_runner = SumoObsRunner(self, cfg.obs)
        self._action_runner = SumoActionRunner(self, cfg.action)
        self._reward_runner = SumoRewardRunner(self, cfg.reward)
        self.close()

    def _launch_env(self, gui: bool = False) -> None:
        # set gui=True can get visualization simulation result with sumo, apply gui=False in the normal training
        # and test setting

        # sumo things - we need to import python modules from the $SUMO_HOME/tools directory
        if 'SUMO_HOME' in os.environ:
            tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
            sys.path.append(tools)
        else:
            sys.exit("please declare environment variable 'SUMO_HOME'")

        # setting the cmd mode or the visual mode
        if gui is False:
            sumoBinary = checkBinary('sumo')
        else:
            sumoBinary = checkBinary('sumo-gui')

        # setting the cmd command to run sumo at simulation time
        sumo_cmd = [
            sumoBinary,
            "-c",
            self._sumocfg_path,
            "--no-step-log",
            "--no-warnings",
        ]
        traci.start(sumo_cmd, label=self._label)
        self._launch_env_flag = True

    def _simulate(self, action: Dict) -> None:
        for tl, a in action.items():
            yellow_phase = a['yellow']
            if yellow_phase is not None:
                self._crosses[tl].set_phase(yellow_phase, self._yellow_duration)
        self._current_steps += self._yellow_duration
        traci.simulationStep(self._current_steps)

        for tl, a in action.items():
            green_phase = a['green']
            self._crosses[tl].set_phase(green_phase, self._yellow_duration + self._green_duration + 1)
        self._current_steps += self._green_duration
        traci.simulationStep(self._current_steps)

    def _set_route_flow(self, route_flow: int) -> None:
        self._sumocfg_path = set_route_flow(
            os.path.dirname(__file__) + '/' + self._cfg.sumocfg_path, route_flow, self._label
        )
        self._route_flow = route_flow
        print("reset sumocfg file to ", self._sumocfg_path)

    def reset(self) -> Any:
        self._current_steps = 0
        self._total_reward = 0
        self._last_action = None
        if self._dynamic_flow:
            route_flow = np.random.randint(*self._flow_range) * 100
            self._set_route_flow(route_flow)
        self._crosses.clear()
        self._vehicle_info_dict.clear()
        self._action_runner.reset()
        self._obs_runner.reset()
        self._reward_runner.reset()
        self._launch_env(self._gui)
        for tl in self._cfg.tls:
            self._crosses[tl] = Crossing(tl, self)
            self._crosses[tl].update_timestep()
        return self._obs_runner.get()

    def step(self, action: Any) -> 'BaseEnv.timestep':
        action_per_tl = self._action_runner.get(action)
        self._simulate(action_per_tl)
        for cross in self._crosses.values():
            cross.update_timestep()
        obs = self._obs_runner.get()
        reward = self._reward_runner.get()
        self._total_reward += reward
        done = self._current_steps > self._max_episode_steps
        info = {}
        if done:
            info['final_eval_reward'] = self._total_reward
            self.close()
        reward = to_ndarray([reward], dtype=np.float32)
        return BaseEnvTimestep(obs, reward, done, info)

    def seed(self, seed: int, dynamic_seed: bool = True) -> None:
        self._seed = seed
        self._dynamic_seed = dynamic_seed
        np.random.seed(self._seed)

    def close(self) -> None:
        r"""
        close traci, set launch_env_flag as False
        """
        if self._launch_env_flag:
            self._launch_env_flag = False
            traci.close()

    def info(self) -> 'BaseEnvInfo':
        info_data = {
            'agent_num': len(self._tls),
            'obs_space': self._obs_runner.info,
            'act_space': self._action_runner.info,
            'rew_space': len(self._tls),
            'use_wrappers': False
        }
        return BaseEnvInfo(**info_data)

    def __repr__(self) -> str:
        return "SumoEnv"

    @property
    def vehicle_info(self) -> Dict[str, Dict]:
        return self._vehicle_info_dict

    @property
    def crosses(self) -> Dict[int, Crossing]:
        return self._crosses

    @property
    def duration(self) -> Tuple[float]:
        return self._green_duration, self._yellow_duration
