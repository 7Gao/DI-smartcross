Reinforcement Learning Environments
########################################

.. toctree::
    :maxdepth: 2


SUMO Environment
====================

Configuration
-----------------

The configuration of sumo env is stored in a config ``.yaml`` file. You can look at the default config file to see how to modify env settings.

.. code:: python

    import yaml
    from easy_dict import EasyDict
    from smartcross.env import SumoEnv

    with open('smartcross/envs/sumo_wj3_default_config.yaml') as f:
        cfg = yaml.safe_load(f)
    cfg = EasyDict(cfg)
    env = SumoEnv(config=cfg.env)

The env configuration consists of basic definition and observation\\action\\reward settings. The basic definition includes the cumo config file, episode length and light duration. The obs-action-reward define the detail setting of each contains.

.. code:: yaml

    env:
        sumocfg_path: 'wj3/rl_wj.sumocfg'
        max_episode_steps: 1500
        green_duration: 10
        yellow_duration: 3
        obs:
            ...
        action:
            ...
        reward:
            ...

Observation
----------------

We provide several types of observations of a traffic cross. If `use_centrolized_obs` is set to `True`, the observation of each cross will be concatenated into one vector. The contents of the observation can be modified by setting `obs_type`. The following observation is supported now.

- phase: One-hot phase vector of current cross signal
- lane_pos_vec: Lane occupancy in each grid position. The grid num can be set with `lane_grid_num`
- traffic_volume: Traffic volume of each lane. Vehicle num / lane length * volume ratio
- queue_len: Vehicle waiting queue length of each lane. Waiting num / lane length * volume ratio

Action
-------------

Sumo environment supports changing cross signal to target phase. The action space is set to multi-discrete for each cross to reduce action num.

Reward
-------------

The reward can be set with `reward_type`. Reward of each cross is calculated separately. If `use_centrolized_obs` is set True, the reward of each cross will be summed up.

- queue_len: Vehicle waiting queue num of each lane
- wait_time: Wait time increment of vehicles in each lane
- delay_time: Delay time of all vehicles in incomming and outgoing lanes
- pressure: Pressure of a cross

Multi-agent
---------------

**DI-smartcross** supports a one-step configurable multi-agent RL training.
It is only necessary to add ``multi_agent`` in **DI-engine** config file to convert common PPO into MAPPO,
and change the ``use_centrolized_obs`` in environment config into ``True``. The policy and observations can
be automatically changed to run individual agent for each cross.


CityFlow Environment
=============================

Configuration
-----------------

CityFlow simulator has its own config `json` file, with roadnet file, flow file and replay file defined in it.
DI-smartcross adds some extra configs together with CityFlow's config file path in DI-engine's env config.

.. code:: python

    main_config = dict(
        env=dict(
            obs_type=['phase', 'lane_vehicle_num', 'lane_waiting_vehicle_num'],
            max_episode_duration=1000,
            green_duration=30,
            yellow_duration=5,
            red_duration=0,
            ...
        ),
        ...
    )

Observation
----------------

We provide several types of observations of each cross.

- phase: One-hot phase vector of current cross signal
- lane_vehicle_num: vehicle nums of each incoming lane
- lane_waiting_vehicle_num: waiting vehicle nums of each incoming lane

Action
-------------

CityFlow environment supports changing cross signal to target phase. The action space is set to multi-discrete for each cross to reduce action num.

Reward
-------------

CityFlow environment uses pressure of each cross as reward


Roadnets
==============

.. toctree::
    :maxdepth: 1

    envs/wj3_env
    envs/rl_arterial7_env
    envs/cf_grid_env

.. `Beijing Wangjing 3 Crossings <./envs/wj3_env.html>`_
.. -----------------------------------------------------------------

.. `RL Arterial 7 Crossings <./envs/rl_arterial7_env.html>`_
.. -----------------------------------------------------------------

.. `CityFlow Grid Env <./envs/cf_grid_env.html>`_
.. -----------------------------------------------------------------
