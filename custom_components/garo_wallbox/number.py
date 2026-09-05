from typing import Callable, Awaitable
from dataclasses import dataclass


from homeassistant.core import HomeAssistant
from homeassistant.const import EntityCategory, UnitOfPower
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)

from .garo import GaroStatus, const
from .coordinator import GaroDeviceCoordinator, GaroMeterCoordinator
from .base import GaroEntity, GaroMeterEntity, GaroMeter
from .const import DOMAIN,COORDINATOR
from . import GaroConfigEntry

@dataclass(frozen=True, kw_only=True)
class GaroNumberEntityDescription(NumberEntityDescription):
    """Describes Garo Number entity."""
    get_value: Callable[[GaroStatus], int]
    set_value: Callable[[int], Awaitable]
    is_available: Callable[[], bool] | None = None

@dataclass(frozen=True, kw_only=True)
class GaroMeterNumberEntityDescription(NumberEntityDescription):
    """Describes Garo Number entity."""
    get_value: Callable[[GaroMeter], int]
    set_value: Callable[[int], Awaitable]
    is_available: Callable[[], bool] | None = None

async def async_setup_entry(hass: HomeAssistant, entry: GaroConfigEntry, async_add_entities):
    """Set up using config_entry."""
    coordinator = entry.runtime_data.coordinator
    configuration = coordinator.config
    entities:list[NumberEntity] =[
        GaroNumberEntity(coordinator, entry, description) for description in [
            GaroNumberEntityDescription(
                key="current_limit",
                translation_key="current_limit",
                name="Current Limit",
                icon="mdi:gauge",
                native_max_value=configuration.max_charge_current,
                native_min_value=6,
                native_step=1,
                native_unit_of_measurement="A",
                get_value=lambda status: status.current_limit,
                set_value=lambda value: coordinator.async_set_current_limit(value),
                is_available=lambda: coordinator.config.charge_limit_enabled,
            ),
        ]]
    if entry.runtime_data.meter_coordinator:
        meter_coordinator = entry.runtime_data.meter_coordinator
        def add_meter_entities(meter: GaroMeter):
            entities.extend(GaroMeterNumberEntity(meter_coordinator, entry, description, meter) for description in [    
                GaroMeterNumberEntityDescription(
                    key="meter_mains_voltage",
                    translation_key="meter_mains_voltage",
                    name="Mains voltage",
                    icon="mdi:sine-wave",
                    native_max_value=280,
                    native_min_value=100,
                    native_step=1,
                    native_unit_of_measurement="V",
                    mode=NumberMode.BOX,
                    entity_category=EntityCategory.DIAGNOSTIC,
                    get_value=lambda status: meter_coordinator.voltage,
                    set_value=lambda value: meter_coordinator.async_set_voltage(value),
                    is_available=lambda: True,
                    )])
        if meter_coordinator.has_external_meter:
            add_meter_entities(meter_coordinator.external_meter)
        if meter_coordinator.has_central100_meter:
            add_meter_entities(meter_coordinator.central100_meter)
        if meter_coordinator.has_central101_meter:
            add_meter_entities(meter_coordinator.central101_meter)

        def add_lb_entity(
            meter: GaroMeter,
            key: str,
            name: str,
            icon: str,
            maximum: int,
            minimum: int,
            unit: str,
            get_value: Callable[[], int],
            set_value: Callable[[int], Awaitable],
            device_class: NumberDeviceClass | None = None,
        ):
            entities.append(GaroLoadBalancingNumberEntity(
                meter_coordinator,
                coordinator,
                entry,
                GaroMeterNumberEntityDescription(
                    key=key,
                    translation_key=key,
                    name=name,
                    icon=icon,
                    device_class=device_class,
                    native_max_value=maximum,
                    native_min_value=minimum,
                    native_step=1,
                    native_unit_of_measurement=unit,
                    mode=NumberMode.BOX,
                    get_value=lambda _: get_value(),
                    set_value=set_value,
                    is_available=lambda: True,
                ),
                meter,
            ))

        def add_lb_meter_entities(
            meter: GaroMeter,
            meter_number: int,
            get_fuse: Callable[[], int],
            set_fuse: Callable[[int], Awaitable],
            get_power: Callable[[], int],
            set_power: Callable[[int], Awaitable],
        ):
            max_fuse = 2500 if configuration.lb_version2 else 63
            add_lb_entity(
                meter,
                f"load_balancing_current_{meter_number}",
                f"Meter {meter_number} Current Limit",
                "mdi:current-ac",
                max_fuse,
                16,
                "A",
                get_fuse,
                set_fuse,
            )
            add_lb_entity(
                meter,
                f"load_balancing_power_{meter_number}",
                f"Meter {meter_number} Power Limit",
                "mdi:transmission-tower",
                250,
                0,
                UnitOfPower.KILO_WATT,
                get_power,
                set_power,
                NumberDeviceClass.POWER,
            )

        if meter_coordinator.has_lb_config:
            if meter_coordinator.has_central100_meter:
                add_lb_meter_entities(
                    meter_coordinator.central100_meter,
                    100,
                    lambda: meter_coordinator.lb_config.fuse,
                    meter_coordinator.async_set_lb_fuse,
                    lambda: meter_coordinator.lb_config.power,
                    meter_coordinator.async_set_lb_power,
                )
            if meter_coordinator.has_central101_meter:
                add_lb_meter_entities(
                    meter_coordinator.central101_meter,
                    101,
                    lambda: meter_coordinator.lb_config.fuse101,
                    meter_coordinator.async_set_lb_fuse101,
                    lambda: meter_coordinator.lb_config.power101,
                    meter_coordinator.async_set_lb_power101,
                )
    async_add_entities(entities)


class GaroNumberEntity(GaroEntity, NumberEntity):

    entity_description: GaroNumberEntityDescription

    def __init__(self, coordinator: GaroDeviceCoordinator, entry, description: GaroNumberEntityDescription):
        self.entity_description = description
        super().__init__(coordinator, entry, description.key)
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""        
        return self.entity_description.is_available() and super().available if self.entity_description.is_available else super().available

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        value = int(value)
        await self.entity_description.set_value(value)
        self._attr_native_value = value
        self.async_write_ha_state()

    def _async_update_attrs(self) -> None:
        self._attr_native_value = self.entity_description.get_value(self.coordinator.status)

class GaroMeterNumberEntity(GaroMeterEntity, NumberEntity):

    entity_description: GaroMeterNumberEntityDescription

    def __init__(self, coordinator: GaroMeterCoordinator, entry, description: GaroMeterNumberEntityDescription, meter: GaroMeter):
        self.entity_description = description
        super().__init__(coordinator, entry, description.key, meter)
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""        
        return self.entity_description.is_available() and super().available if self.entity_description.is_available else super().available

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        value = int(value)
        await self.entity_description.set_value(value)
        self._attr_native_value = value
        self.async_write_ha_state()

    def _async_update_attrs(self) -> None:
        self._attr_native_value = self.entity_description.get_value(self._meter)


class GaroLoadBalancingNumberEntity(GaroMeterNumberEntity):
    """Number entity grouped under a dedicated load-balancing device."""

    def __init__(
        self,
        coordinator: GaroMeterCoordinator,
        device_coordinator: GaroDeviceCoordinator,
        entry,
        description: GaroMeterNumberEntityDescription,
        meter: GaroMeter,
    ):
        super().__init__(coordinator, entry, description, meter)
        self._attr_unique_id = (
            f"{device_coordinator.device_id}-load_balancing-{description.key}"
        )
        self._attr_device_info = device_coordinator.load_balancing_device_info
