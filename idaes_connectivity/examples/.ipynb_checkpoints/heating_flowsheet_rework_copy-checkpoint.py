from pathlib import Path
import numpy as np
import math
import random
import json
import logging
from io import StringIO
import pandas as pd
import threading
import queue

from matplotlib import pyplot as plt
from matplotlib import rc
import matplotlib.ticker as ticker

from pyomo.environ import (
    ConcreteModel,
    Var,
    Set,
    RangeSet,
    Constraint,
    Objective,
    Param,
    Block,
    value,
    NonNegativeReals,
    SolverFactory,
    TransformationFactory,
    assert_optimal_termination,
    units as pyunits,
)

from pyomo.common.log import LoggingIntercept
from pyomo.util.infeasible import (
    log_active_constraints,
    log_close_to_bounds,
    log_infeasible_bounds,
    log_infeasible_constraints,
)

from pyomo.util.check_units import (
    assert_units_consistent,
    assert_units_equivalent,
    check_units_equivalent,
)
from pyomo.network import Arc, Port
from idaes.core import FlowsheetBlock
from idaes.core import MaterialBalanceType, MaterialFlowBasis
from idaes.models.unit_models import (
    Feed,
    Product,
    Separator,
    SplittingType,
    EnergySplittingType,
    Mixer,
    MixingType,
    MomentumMixingType,
)

# from watertap.core.solvers import get_solver
from idaes.core.solvers import get_solver
import idaes.core.util.scaling as iscale
from idaes.core.util.scaling import get_scaling_factor
from idaes.core.scaling import (
    CustomScalerBase,
    set_scaling_factor,
    report_scaling_factors,
)
import idaes.logger as idaeslog
from idaes.core.util.initialization import propagate_state
from idaes.core.util.model_statistics import degrees_of_freedom

import idaes_models.models.unit_models.water_prop_pack as props2
from idaes_models.models.unit_models.dispatches_elec_splitter import (
    ElectricalSplitter,
    ElectricalSplitterScaler,
)
from idaes_models.models.unit_models.battery import BatteryStorage, BatteryStorageScaler
from idaes_models.models.unit_models.gas_boiler_pp import (
    DetailedGasBoiler,
    GasBoilerScaler,
)
from idaes_models.models.unit_models.heat_pump_mod import HeatPump, HeatPumpScaler
from idaes_models.models.unit_models.electricity_grid import (
    ElectricalGrid,
    ElectricalGridScaler,
)
from idaes_models.models.unit_models.thermal_plant_load import (
    EnergySinks,
    EnergySinkScaler,
)
from idaes_models.models.unit_models.elec_mixer import (
    ElectricalMixer,
    ElectricalMixerScaler,
)
from idaes_models.models.unit_models.water_tank import TankStorage, TankStorageScaler
from idaes_models.models.system_costing_v3 import add_costing, cost_scaling
from idaes_models.models.system_emissions import add_emissions, emissions_scaling
from idaes_models.models.model_postprocessing import (
    extract_results_old,
    extract_results_new,
)
from idaes_models.models.plotting_function import plots_old, plots_new

timestep_hrs = 1

__author__ = "Oluwamayowa Amusat"


def simulate_price_signal(no_timesteps):
    price_signal = [
        0.11,
        0.09,
        0.09,
        0.10,
        0.31,
        0.46,
        0.51,
        0.46,
        0.38,
        0.39,
        0.46,
        0.50,
        0.64,
        0.48,
        0.38,
        0.37,
        0.39,
        0.61,
        1.14,
        0.93,
        0.62,
        0.44,
        0.29,
        0.20,
    ]
    price_signal = price_signal * (no_timesteps // 24)
    time_steps = [i for i in range(0, no_timesteps)]
    cost_dict = {k: v for (k, v) in zip(time_steps, price_signal)}
    return cost_dict


def simulate_inlet_hot_water_temperatures(no_timesteps):
    random.seed(0)
    lb, ub = 8, 16
    time_steps = [i for i in range(0, no_timesteps)]
    temps = [273.15 + random.randint(lb, ub) for i in range(0, no_timesteps)]
    # cost_dict = {k : v for (k , v) in zip(time_steps, temps)}
    return temps


def add_grid_connection(model, grid_limits_mw=None):
    model.electrical_grid = ElectricalGrid()
    if grid_limits_mw is not None:
        model.electrical_grid.grid_capacity.fix(grid_limits_mw)
    return model.electrical_grid


def add_battery(model, batt_mw=None):
    model.battery = BatteryStorage()
    model.battery.dt.set_value(timestep_hrs)
    if batt_mw is not None:
        model.battery.capacity_power.fix(batt_mw)
    return model.battery


def add_detailed_gas_boiler(model, prop_pack):
    model.gas_boiler = DetailedGasBoiler(property_package=prop_pack)
    return model.gas_boiler


def add_heat_pump(model, prop_pack):
    model.heat_pump = HeatPump(property_package=prop_pack)
    return model.heat_pump


def add_water_tank(model, prop_pack):
    model.hw_tank = TankStorage(property_package=prop_pack)
    model.hw_tank.Q_elect.fix(0)
    return model.hw_tank


def add_thermal_plant_loads(model, prop_pack):
    model.plant_load = EnergySinks(property_package=prop_pack)
    return model.plant_load


def build_model(no_timesteps):
    grid_electricity_sinks = ["battery", "heat_pump"]
    battery_electricity_sinks = ["heat_pump", "electrical_load"]
    heat_pump_electricity_sources = ["battery", "grid"]
    thermal_energy_sources = ["from_hp", "from_boiler"]
    plant_load_heat_sources = ["from_direct", "from_tank"]
    tank_water_sources = ["from_load", "from_generation"]
    tank_water_sinks = ["to_hp", "to_boiler", "to_plant"]

    m = ConcreteModel()
    m.periods = RangeSet(0, no_timesteps - 1)
    m.fs = FlowsheetBlock(m.periods, dynamic=False)

    for p in m.periods:
        # Property package
        m.fs[p].water_properties = props2.WaterParameterBlock()

        m.fs[p].plant_load = add_thermal_plant_loads(m.fs[p], m.fs[p].water_properties)
        m.fs[p].electrical_grid = add_grid_connection(m.fs[p])
        m.fs[p].battery = add_battery(m.fs[p])
        m.fs[p].grid_splitter = ElectricalSplitter(
            outlet_list=grid_electricity_sinks, add_split_fraction_vars=False
        )
        m.fs[p].gas_boiler = add_detailed_gas_boiler(m.fs[p], m.fs[p].water_properties)
        m.fs[p].heat_pump = add_heat_pump(m.fs[p], m.fs[p].water_properties)
        m.fs[p].hw_tank = add_water_tank(m.fs[p], m.fs[p].water_properties)
        m.fs[p].heat_pump_electricity_mixer = ElectricalMixer(
            inlet_list=heat_pump_electricity_sources
        )
        m.fs[p].thermal_generation_mixer = Mixer(
            property_package=m.fs[p].water_properties,
            inlet_list=thermal_energy_sources,
            material_balance_type=MaterialBalanceType.componentPhase,
            momentum_mixing_type=MomentumMixingType.equality,
            # equality or minimize
            energy_mixing_type=MixingType.extensive,
        )
        m.fs[p].thermal_generation_splitter = Separator(
            property_package=m.fs[p].water_properties,
            outlet_list=["to_plant", "to_tank"],
            split_basis=SplittingType.totalFlow,
            energy_split_basis=EnergySplittingType.equal_temperature,
            material_balance_type=MaterialBalanceType.componentPhase,
        )
        m.fs[p].thermal_demand_mixer = Mixer(
            property_package=m.fs[p].water_properties,
            inlet_list=plant_load_heat_sources,
            momentum_mixing_type=MomentumMixingType.equality,  # .equality,
            energy_mixing_type=MixingType.extensive,
        )
        m.fs[p].tank_mixer = Mixer(
            property_package=m.fs[p].water_properties,
            inlet_list=tank_water_sources,
            momentum_mixing_type=MomentumMixingType.equality,  # .equality,
            energy_mixing_type=MixingType.extensive,
        )
        m.fs[p].feed_water = Feed(property_package=m.fs[p].water_properties)
        m.fs[p].waste_water = Product(property_package=m.fs[p].water_properties)
        m.fs[p].tank_water_splitter = Separator(
            property_package=m.fs[p].water_properties,
            outlet_list=tank_water_sinks,
            split_basis=SplittingType.totalFlow,
            energy_split_basis=EnergySplittingType.equal_temperature,
            material_balance_type=MaterialBalanceType.componentPhase,
        )

        m.fs[p].grid_power_consumed = Arc(
            source=m.fs[p].electrical_grid.power_supplied,
            dest=m.fs[p].grid_splitter.electricity_in,
        )
        m.fs[p].gridsplitter_to_battery = Arc(
            source=m.fs[p].grid_splitter.battery_port, dest=m.fs[p].battery.power_in
        )
        m.fs[p].gridsplitter_to_heatpump = Arc(
            source=m.fs[p].grid_splitter.heat_pump_port,
            dest=m.fs[p].heat_pump_electricity_mixer.grid_port,
        )
        m.fs[p].battery_to_heatpump = Arc(
            source=m.fs[p].battery.power_out,
            dest=m.fs[p].heat_pump_electricity_mixer.battery_port,
        )
        m.fs[p].electricity_to_heatpump = Arc(
            source=m.fs[p].heat_pump_electricity_mixer.electricity_out,
            dest=m.fs[p].heat_pump.power_in,
        )

        m.fs[p].tank_to_separator = Arc(
            source=m.fs[p].hw_tank.outlet_water, dest=m.fs[p].tank_water_splitter.inlet
        )
        m.fs[p].tank_separator_to_boiler = Arc(
            source=m.fs[p].tank_water_splitter.to_boiler,
            dest=m.fs[p].gas_boiler.inlet_water,
        )
        m.fs[p].tank_separator_to_hp = Arc(
            source=m.fs[p].tank_water_splitter.to_hp,
            dest=m.fs[p].heat_pump.hotside_inlet_water,
        )
        m.fs[p].tank_separator_to_plant = Arc(
            source=m.fs[p].tank_water_splitter.to_plant,
            dest=m.fs[p].thermal_demand_mixer.from_tank,
        )
        m.fs[p].boiler_thermal_generation_mixing = Arc(
            source=m.fs[p].gas_boiler.outlet_water,
            dest=m.fs[p].thermal_generation_mixer.from_boiler,
        )
        m.fs[p].hp_thermal_generation_mixing = Arc(
            source=m.fs[p].heat_pump.hotside_outlet_water,
            dest=m.fs[p].thermal_generation_mixer.from_hp,
        )
        m.fs[p].district_water_to_hp = Arc(
            source=m.fs[p].feed_water.outlet,
            dest=m.fs[p].heat_pump.coldside_inlet_water,
        )
        m.fs[p].hp_to_district_water = Arc(
            source=m.fs[p].heat_pump.coldside_outlet_water,
            destination=m.fs[p].waste_water.inlet,
        )
        m.fs[p].mixer_to_splitter = Arc(
            source=m.fs[p].thermal_generation_mixer.outlet,
            dest=m.fs[p].thermal_generation_splitter.inlet,
        )
        m.fs[p].direct_generation_to_load = Arc(
            source=m.fs[p].thermal_generation_splitter.to_plant,
            dest=m.fs[p].thermal_demand_mixer.from_direct,
        )
        m.fs[p].total_stream_to_load = Arc(
            source=m.fs[p].thermal_demand_mixer.outlet,
            destination=m.fs[p].plant_load.inlet_water,
        )
        m.fs[p].load_to_mixer_pretank = Arc(
            source=m.fs[p].plant_load.outlet_water, dest=m.fs[p].tank_mixer.from_load
        )
        m.fs[p].generation_to_mixer_pretank = Arc(
            source=m.fs[p].thermal_generation_splitter.to_tank,
            destination=m.fs[p].tank_mixer.from_generation,
        )
        m.fs[p].water_bleeding_pretank = Arc(
            source=m.fs[p].tank_mixer.outlet, destination=m.fs[p].hw_tank.inlet_water
        )

    # ========================
    # Battery constraints:
    # ========================
    # 1 . Capacity of battery in MW must be same across all time periods
    @m.Constraint(m.periods)
    def eq_battery_power_capacity_linking(m, key):
        if key == max(list(m.periods)):
            return m.fs[key].battery.capacity_power == m.fs[0].battery.capacity_power
        else:
            return (
                m.fs[key].battery.capacity_power == m.fs[key + 1].battery.capacity_power
            )

    # 2 . Capacity of battery in MWh must be same across all time periods
    @m.Constraint(m.periods)
    def eq_battery_energy_capacity_linking(m, key):
        if key == max(list(m.periods)):
            return (
                m.fs[key].battery.capacity_energy - m.fs[0].battery.capacity_energy == 0
            )
        else:
            return (
                m.fs[key].battery.capacity_energy
                - m.fs[key + 1].battery.capacity_energy
                == 0
            )

    # 3. Energy at start of next time period should be same as end of previous time perios, and first must equal last
    @m.Constraint(m.periods)
    def eq_battery_storage_level_linking(m, key):
        if key == max(list(m.periods)):
            return (
                m.fs[key].battery.storage_level[0] - m.fs[0].battery.initial_state == 0
            )  # constraint to ensure no energy is "magically" used
        else:
            return (
                m.fs[key].battery.storage_level[0] - m.fs[key + 1].battery.initial_state
                == 0
            )

    # ========================
    # Grid constraints:
    # ========================
    # 1. Capacity of grid in MW must be same across all time periods
    @m.Constraint(m.periods)
    def eq_grid_power_capacity_linking(m, key):
        if key == max(list(m.periods)):
            return (
                m.fs[key].electrical_grid.grid_capacity
                - m.fs[0].electrical_grid.grid_capacity
                == 0
            )
        else:
            return (
                m.fs[key].electrical_grid.grid_capacity
                - m.fs[key + 1].electrical_grid.grid_capacity
                == 0
            )

    # 2. Constrain the maximum power that can be drawn from the grid at any one timestep: current assumption: 2.5x load
    @m.Constraint(m.periods)
    def eq_max_grid_capacity(m, key):
        return (
            pyunits.convert(m.fs[key].electrical_grid.E_grid[0], to_units=pyunits.MW)
            <= 2.5 * pyunits.MW
        )

    # ========================
    # Boiler constraints:
    # ========================
    # 1 . Capacity of boiler in MW must be same across all time periods
    @m.Constraint(m.periods)
    def eq_boiler_power_capacity_linking(m, key):
        if key == max(list(m.periods)):
            return (
                m.fs[key].gas_boiler.capacity_power - m.fs[0].gas_boiler.capacity_power
                == 0
            )
        else:
            return (
                m.fs[key].gas_boiler.capacity_power
                - m.fs[key + 1].gas_boiler.capacity_power
                == 0
            )

    # ========================
    # Heat pump constraints:
    # ========================
    # 1 . Capacity of HP in kW must be same across all time periods
    @m.Constraint(m.periods)
    def eq_hp_power_capacity_linking(m, key):
        if key == max(list(m.periods)):
            return (
                m.fs[key].heat_pump.capacity_power - m.fs[0].heat_pump.capacity_power
                == 0
            )
        else:
            return (
                m.fs[key].heat_pump.capacity_power
                - m.fs[key + 1].heat_pump.capacity_power
                == 0
            )

    # ========================
    # Tank constraints:
    # ========================
    # 1 . Volume of water tank must be same across all time periods
    @m.Constraint(m.periods)
    def eq_hw_tank_volume_linking(m, key):
        if key == max(list(m.periods)):
            return m.fs[key].hw_tank.V_tank - m.fs[0].hw_tank.V_tank == 0
        else:
            return m.fs[key].hw_tank.V_tank - m.fs[key + 1].hw_tank.V_tank == 0

    # 3 . Capacity of tank in MWh must be same across all time periods
    @m.Constraint(m.periods)
    def eq_hw_tank_energy_capacity_linking(m, key):
        if key == max(list(m.periods)):
            return (
                m.fs[key].hw_tank.capacity_energy - m.fs[0].hw_tank.capacity_energy == 0
            )
        else:
            return (
                m.fs[key].hw_tank.capacity_energy
                - m.fs[key + 1].hw_tank.capacity_energy
                == 0
            )

    # # 4. Energy mass at start of next time period should be same as end of previous time perios, and first must equal last
    # @m.Constraint(m.periods)
    # def eq_hw_tank_storage_level_linking(m, key):
    #     if key == max(list(m.periods)):
    #         return m.fs[key].hw_tank.storage_level[0] - m.fs[
    #             0].hw_tank.initial_state_energy == 0  # m.fs[key].hw_tank.storage_level[0] - m.fs[0].hw_tank.initial_state_energy == 0
    #     else:
    #         return m.fs[key].hw_tank.storage_level[0] - m.fs[key + 1].hw_tank.initial_state_energy == 0

    # 5. Water mass at start of next time period should be same as end of previous time perios, and first must equal last
    @m.Constraint(m.periods)
    def eq_hw_tank_water_level_linking(m, key):
        if key == max(list(m.periods)):
            return m.fs[key].hw_tank.M[0] - m.fs[0].hw_tank.initial_state_mass == 0
        else:
            return (
                m.fs[key].hw_tank.M[0] - m.fs[key + 1].hw_tank.initial_state_mass == 0
            )

    # 6. Temperature at start of next time period should be same as end of previous time perios, and first must equal last
    # Andrew advice: use slacks instead of these start=end constraints?
    @m.Constraint(m.periods)
    def eq_hw_tank_temperature_linking(m, key):
        if key == max(list(m.periods)):
            return (
                m.fs[key].hw_tank.T[0] - m.fs[0].hw_tank.initial_state_temperature == 0
            )
        else:
            return (
                m.fs[key].hw_tank.T[0] - m.fs[key + 1].hw_tank.initial_state_temperature
                == 0
            )

    TransformationFactory("network.expand_arcs").apply_to(m)

    return m


class FlowsheetScaler(CustomScalerBase):

    def variable_scaling_routine(
        self, model, overwrite: bool = False, submodel_scalers: dict = None
    ):
        pass

    def constraint_scaling_routine(
        self, model, overwrite: bool = False, submodel_scalers: dict = None
    ):
        pass

        for j, c in model.eq_grid_power_capacity_linking.items():
            # self.scale_constraint_by_nominal_value(c, scheme="inverse_maximum", overwrite=overwrite,)
            self.scale_constraint_by_component(
                c,
                model.fs[0].electrical_grid.grid_capacity,
                overwrite=overwrite,
            )

        for j, c in model.eq_battery_power_capacity_linking.items():
            self.scale_constraint_by_component(
                c,
                model.fs[0].battery.capacity_power,
                overwrite=overwrite,
            )

        for j, c in model.eq_battery_energy_capacity_linking.items():
            self.scale_constraint_by_component(
                c,
                model.fs[0].battery.capacity_energy,
                overwrite=overwrite,
            )

        for j, c in model.eq_battery_storage_level_linking.items():
            self.scale_constraint_by_component(
                c,
                model.fs[0].battery.storage_level[0],
                overwrite=overwrite,
            )

        # for j, c in model.eq_hw_tank_storage_level_linking.items():
        #     self.scale_constraint_by_component(c, model.fs[0].hw_tank.storage_level[0], overwrite=overwrite)

        for j, c in model.eq_max_grid_capacity.items():
            self.scale_constraint_by_component(
                c, model.fs[0].electrical_grid.grid_capacity, overwrite=overwrite
            )

        for j, c in model.eq_boiler_power_capacity_linking.items():
            self.scale_constraint_by_component(
                c, model.fs[0].gas_boiler.capacity_power, overwrite=overwrite
            )

        for j, c in model.eq_hp_power_capacity_linking.items():
            self.scale_constraint_by_component(
                c, model.fs[0].heat_pump.capacity_power, overwrite=overwrite
            )

        for j, c in model.eq_hw_tank_volume_linking.items():
            self.scale_constraint_by_component(
                c, model.fs[0].hw_tank.V_tank, overwrite=overwrite
            )

        for j, c in model.eq_hw_tank_energy_capacity_linking.items():
            self.scale_constraint_by_component(
                c, model.fs[0].hw_tank.capacity_energy, overwrite=overwrite
            )

        for j, c in model.eq_hw_tank_temperature_linking.items():
            self.scale_constraint_by_component(
                c, model.fs[0].hw_tank.T[0], overwrite=overwrite
            )

        for j, c in model.eq_hw_tank_water_level_linking.items():
            self.scale_constraint_by_component(
                c, model.fs[0].hw_tank.M_tank, overwrite=overwrite
            )


def add_scaling(model):
    f_sf = 1e-3
    enth_sf = 1e-6
    DEFAULT_SCALING_FACTORS = {
        "flow_mass_phase_comp": f_sf,
        "pressure": 1e-5,
        "temperature": 1e-2,
        "split_fraction": 1,
        "enth_mass_phase": enth_sf,
    }
    DEFAULT_SCALING_FACTORS["enth_flow_phase"] = (
        DEFAULT_SCALING_FACTORS["flow_mass_phase_comp"]
        * DEFAULT_SCALING_FACTORS["enth_mass_phase"]
    )
    overwrite = False

    for p in model.periods:
        scaler = EnergySinkScaler()
        scaler.scale_model(
            model.fs[p].plant_load,
            submodel_scalers={
                "control_volume.properties_in": props2.WaterPropertiesScaler,
                "control_volume.properties_out": props2.WaterPropertiesScaler,
            },
        )

        scaler = GasBoilerScaler()
        set_scaling_factor(
            model.fs[p].gas_boiler.properties_in[0].flow_mass_phase_comp["Liq", "H2O"],
            f_sf,
        )
        set_scaling_factor(
            model.fs[p].gas_boiler.properties_out[0].flow_mass_phase_comp["Liq", "H2O"],
            f_sf,
        )
        set_scaling_factor(
            model.fs[p].gas_boiler.properties_in[0].enth_mass_phase["Liq"], enth_sf
        )
        set_scaling_factor(
            model.fs[p].gas_boiler.properties_out[0].enth_mass_phase["Liq"], enth_sf
        )
        scaler.scale_model(
            model.fs[p].gas_boiler,
            submodel_scalers={
                "control_volume.properties_in": props2.WaterPropertiesScaler,
                "control_volume.properties_out": props2.WaterPropertiesScaler,
            },
        )

        scaler = HeatPumpScaler()
        set_scaling_factor(
            model.fs[p]
            .heat_pump.properties_in_hotside[0]
            .flow_mass_phase_comp["Liq", "H2O"],
            f_sf,
        )
        set_scaling_factor(
            model.fs[p]
            .heat_pump.properties_out_hotside[0]
            .flow_mass_phase_comp["Liq", "H2O"],
            f_sf,
        )
        set_scaling_factor(
            model.fs[p]
            .heat_pump.properties_in_coldside[0]
            .flow_mass_phase_comp["Liq", "H2O"],
            f_sf,
        )
        set_scaling_factor(
            model.fs[p]
            .heat_pump.properties_out_coldside[0]
            .flow_mass_phase_comp["Liq", "H2O"],
            f_sf,
        )
        set_scaling_factor(
            model.fs[p].heat_pump.properties_in_hotside[0].enth_mass_phase["Liq"],
            enth_sf,
        )
        set_scaling_factor(
            model.fs[p].heat_pump.properties_out_hotside[0].enth_mass_phase["Liq"],
            enth_sf,
        )
        set_scaling_factor(
            model.fs[p].heat_pump.properties_in_coldside[0].enth_mass_phase["Liq"],
            enth_sf,
        )
        set_scaling_factor(
            model.fs[p].heat_pump.properties_out_coldside[0].enth_mass_phase["Liq"],
            enth_sf,
        )
        scaler.scale_model(
            model.fs[p].heat_pump,
            submodel_scalers={
                "control_volume.properties_in_hotside": props2.WaterPropertiesScaler,
                "control_volume.properties_out_hotside": props2.WaterPropertiesScaler,
                "control_volume.properties_in_coldside": props2.WaterPropertiesScaler,
                "control_volume.properties_out_coldside": props2.WaterPropertiesScaler,
            },
        )

        scaler = TankStorageScaler()
        set_scaling_factor(
            model.fs[p].hw_tank.properties_in[0].flow_mass_phase_comp["Liq", "H2O"],
            f_sf,
        )
        set_scaling_factor(
            model.fs[p].hw_tank.properties_out[0].flow_mass_phase_comp["Liq", "H2O"],
            f_sf,
        )
        set_scaling_factor(
            model.fs[p].hw_tank.properties_in[0].enth_mass_phase["Liq"], enth_sf
        )
        set_scaling_factor(
            model.fs[p].hw_tank.properties_out[0].enth_mass_phase["Liq"], enth_sf
        )
        scaler.scale_model(
            model.fs[p].hw_tank,
            submodel_scalers={
                "control_volume.properties_in": props2.WaterPropertiesScaler,
                "control_volume.properties_out": props2.WaterPropertiesScaler,
            },
        )

        scaler = BatteryStorageScaler()
        scaler.scale_model(
            model.fs[p].battery,
        )

        scaler = ElectricalGridScaler()
        scaler.scale_model(
            model.fs[p].electrical_grid,
        )

        scaler = ElectricalSplitterScaler()
        scaler.scale_model(
            model.fs[p].grid_splitter,
        )

        scaler = ElectricalMixerScaler()
        scaler.scale_model(
            model.fs[p].heat_pump_electricity_mixer,
        )

    scaler = FlowsheetScaler()
    scaler.scale_model(model)

    csb = CustomScalerBase()
    for p in model.periods:
        for unit in (
            "feed_water",
            "waste_water",
            "thermal_generation_splitter",
            "tank_water_splitter",
            "thermal_generation_mixer",
            "thermal_demand_mixer",
            "tank_mixer",
        ):
            block = getattr(model.fs[p], unit)
            for v in block.component_data_objects(Var, descend_into=True):
                for k in DEFAULT_SCALING_FACTORS.keys():
                    if k in v.name:
                        csb.set_variable_scaling_factor(
                            v, DEFAULT_SCALING_FACTORS[k], overwrite=overwrite
                        )

    csb = CustomScalerBase()
    for p in model.periods:
        for unit in (
            "thermal_generation_splitter",
            "tank_water_splitter",
            "thermal_generation_mixer",
            "thermal_demand_mixer",
            "tank_mixer",
        ):
            block = getattr(model.fs[p], unit)
            for c in block.component_data_objects(Constraint, descend_into=True):
                csb.scale_constraint_by_nominal_value(
                    c, scheme="inverse_maximum", overwrite=overwrite
                )

    # scale arcs
    csb = CustomScalerBase()
    for p in m.periods:
        arcs_in_period = list(model.fs[p].component_objects(Arc, descend_into=True))
        for arc in arcs_in_period:
            for constr_name, c in arc.component_map(ctype=Constraint).items():
                if "pressure" in constr_name:
                    for index in c:
                        csb.set_constraint_scaling_factor(
                            c[index],
                            DEFAULT_SCALING_FACTORS["pressure"],
                            overwrite=overwrite,
                        )
                if "temperature" in constr_name:
                    for index in c:
                        csb.set_constraint_scaling_factor(
                            c[index],
                            DEFAULT_SCALING_FACTORS["temperature"],
                            overwrite=overwrite,
                        )

    # report_scaling_factors(model.fs[0].heat_pump)
    # report_scaling_factors(model, descend_into=True)
    # assert False

    return model


def instantiate_model(model, data=None):
    # Hot water temperatures
    boiler_efficiency = 0.90
    heat_pump_COP = 3.0
    batt_effs = 0.95
    feedwater_temps = simulate_inlet_hot_water_temperatures(len(model.periods))
    for p in model.periods:
        model.fs[p].feed_water.pressure.fix(101325)
        model.fs[p].feed_water.temperature.fix(feedwater_temps[p])

        # Fix temperatures
        model.fs[p].gas_boiler.properties_out[0].temperature.fix(92 + 273.15)
        model.fs[p].heat_pump.properties_out_hotside[0].temperature.fix(92 + 273.15)
        model.fs[p].plant_load.properties_in[0].temperature.fix(90 + 273.15)
        model.fs[p].plant_load.properties_out[0].temperature.fix(70 + 273.15)
        # Set parameters
        model.fs[p].battery.eta_discharge.set_value(batt_effs)
        model.fs[p].battery.eta_charge.set_value(batt_effs)
        model.fs[p].gas_boiler.eta.set_value(boiler_efficiency)
        model.fs[p].heat_pump.COP.set_value(heat_pump_COP)
        # Set loads
        thermal_load_value = 1e3
        model.fs[p].plant_load.Q_load[0].fix(thermal_load_value)

    return model


def create_steady_state_problem(model):
    # 1. Fix capacities of boiler, gas turbine, battery and tank storage
    for p in model.periods:
        model.fs[p].gas_boiler.capacity_power.fix(3e3)
        model.fs[p].heat_pump.capacity_power.fix(2e3)
        model.fs[p].hw_tank.capacity_energy.fix(8 * 1e3)
        # model.fs[p].mixer_to_splitter_expanded.flow_mass_phase_comp_equality.deactivate()

    # model.fs[0].hw_tank.initial_state_energy.fix(4 * 1e3)

    assert degrees_of_freedom(model) == 0
    return model


def solve_model(model, tol):
    ##########################
    # Fixing currently unused variables
    ##########################
    assert_units_consistent(model)
    # assert False
    solver = get_solver()
    solver.options["nlp_scaling_method"] = "user-scaling"
    solver.options["max_iter"] = 1000
    solver.options["tol"] = tol

    result = solver.solve(model, tee=True)

    output = StringIO()
    with LoggingIntercept(output, "pyomo.util.infeasible", logging.INFO):
        log_infeasible_constraints(m)
    print(output.getvalue().splitlines())

    assert_optimal_termination(result)
    if result.Solver[0]["Termination condition"] == "optimal":
        return result
    else:
        output = StringIO()
        with LoggingIntercept(output, "pyomo.util.infeasible", logging.INFO):
            log_infeasible_constraints(m)
        # print(output.getvalue().splitlines())
        for i in range(0, len(output.getvalue().splitlines())):
            print(output.getvalue().splitlines()[i])


def solve_model_baron(model):
    ##########################
    # Fixing currently unused variables
    ##########################
    assert_units_consistent(model)
    solver = SolverFactory("baron")
    solver.options["maxTime"] = 3000
    result = solver.solve(model, tee=True)
    # result = SolverFactory('baron').solve(model, options={'MaxTime': 1000, 'contol':1e-6})

    output = StringIO()
    with LoggingIntercept(output, "pyomo.util.infeasible", logging.INFO):
        log_infeasible_constraints(m)
    print(output.getvalue().splitlines())

    assert_optimal_termination(result)
    if result.Solver[0]["Termination condition"] == "optimal":
        return result
    else:
        output = StringIO()
        with LoggingIntercept(output, "pyomo.util.infeasible", logging.INFO):
            log_infeasible_constraints(m)
        # print(output.getvalue().splitlines())
        for line in output.getvalue().splitlines():
            print(line)


def create_optimization_problem(model):
    for p in model.periods:
        model.fs[p].gas_boiler.capacity_power.unfix()
        model.fs[p].heat_pump.capacity_power.unfix()
        model.fs[p].hw_tank.capacity_energy.unfix()
    return model


def system_design_information(model):
    design_characteristics = {}
    design_characteristics["Battery capacity (kWh)"] = value(
        model.fs[0].battery.capacity_energy
    )
    # design_characteristics['Battery capacity (kW)'] = value(model.fs[0].battery.capacity_power)
    # design_characteristics['Tank capacity (kWh)'] = value(model.fs[0].hw_tank.capacity_energy)
    design_characteristics["Tank volume (m3)"] = value(model.fs[0].hw_tank.V_tank)
    design_characteristics["Tank water mass (kg)"] = value(model.fs[0].hw_tank.M_tank)
    design_characteristics["Heat pump (kW)"] = value(
        model.fs[0].heat_pump.capacity_power
    )
    design_characteristics["Gas boiler (kW)"] = value(
        model.fs[0].gas_boiler.capacity_power
    )
    design_characteristics["Emissions (M_kg/yr)"] = value(
        model.emissions.total_annual_emissions
    )
    design_characteristics["Capital cost (M_USD)"] = value(
        model.costing.cc.total_capital_cost
    )
    design_characteristics["Operating cost (M_USD/yr)"] = value(
        model.costing.oc.total_operating_cost
    )
    design_characteristics["Annualized cost (M_USD/yr)"] = value(
        m.costing.total_annualized_cost
    )
    return design_characteristics


def extract_and_save_in_background(m, fname, res):
    print("Saving results in background...")
    var_json = extract_results_old(m, fname)
    print("Saving done...")
    res.put(var_json)


# def build():
#     no_timesteps = 168
#     m = build_model(no_timesteps=no_timesteps)
#     return m

# python connectivity.py heating_flowsheet_rework -O hf.html --labels --to html --fs 'fs[0]'
# python connectivity.py heating_flowsheet_rework -O hf.csv --to csv --fs 'fs[0]'


if __name__ == "__main__":
    no_timesteps = 8760
    # Build model
    m = build_model(no_timesteps=no_timesteps)

    # Create and solve square system
    m = instantiate_model(m)
    m = add_scaling(m)
    dof_prefixing = degrees_of_freedom(m)
    print("Degrees of freedom before fixing anything:", dof_prefixing)
    m = create_steady_state_problem(m)
    res = solve_model(m, tol=1e-8)

    # Add costing model to square system case and re-solve
    m = add_costing(m, no_timesteps=no_timesteps)
    m = cost_scaling(m)
    assert degrees_of_freedom(m) == 0
    res = solve_model(m, tol=1e-8)

    # Create optimization problem and re-solve
    m = create_optimization_problem(m)
    assert degrees_of_freedom(m) == dof_prefixing
    res = solve_model(m, tol=1e-8)

    # Add emissions model to optimization problem and re-solve
    m = add_emissions(m, no_timesteps=no_timesteps)
    m = emissions_scaling(m)
    res = solve_model(m, tol=1e-7)
    emissions_ub = math.floor(value(m.emissions.total_annual_emissions) * 10) / 10
    print(f"\nEmissions upper bound: {emissions_ub}")
    base_emissions = round(value(m.emissions.total_annual_emissions), 4)
    base_emissions_design = system_design_information(m)

    # Save results in background
    current_dir = Path(__file__).resolve().parent
    results_path = current_dir / "results"
    m_clone = m.clone()
    results_queue = queue.Queue()
    dump_thread = threading.Thread(
        target=extract_and_save_in_background,
        args=(m_clone, results_path / "model_basecase_8760h_copy.json", results_queue),
    )
    dump_thread.start()

    # 2. Make emissions the objective of optimization problem
    m.objective = Objective(expr=m.emissions.total_annual_emissions)
    res = solve_model(m, tol=1e-8)
    emissions_lb = math.ceil(value(m.emissions.total_annual_emissions) * 10) / 10
    print(f"\nEmissions upper bound: {emissions_lb}")
    best_case_emissions = round(value(m.emissions.total_annual_emissions), 4)
    best_case_emissions_design = system_design_information(m)

    # 3. Add emissions as constraints and re-solve each case
    m.objective = Objective(expr=m.costing.total_annualized_cost)
    emissions_limits_range = np.arange(emissions_lb, emissions_ub, 0.1)
    system_dict = {}
    # base_emissions = round(value(m.emissions.total_annual_emissions), 4)
    # system_dict[base_emissions] = system_design_information(m)
    system_dict[base_emissions] = base_emissions_design
    system_dict[best_case_emissions] = best_case_emissions_design
    for emissions_limit in emissions_limits_range:
        print(f"\nRunning emissions case...{emissions_limit}")
        m.emissions.annual_emissions_limit.value = (
            emissions_limit * pyunits.M_kg / pyunits.yr
        )
        res = solve_model(m, tol=1e-7)
        system_dict[emissions_limit] = system_design_information(m)

    xv = pd.DataFrame(system_dict).T
    xv.to_csv(results_path / "tradeoffs_basecase_copy.csv")

    dump_thread.join()
    var_json = results_queue.get()

    # var_json = extract_results_old(m)
    # plots_old(var_json)

    # # to_json(m, fname="model_state_8760.gz", gz=True, human_read=True)


def build():
    m = build_model(1)
    for idx, data in m.fs.items():
        print("Return the first one")
        return data
