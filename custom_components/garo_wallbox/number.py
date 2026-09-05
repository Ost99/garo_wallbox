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

async def async_setup_entry(
    hass: HomeAssistant,
    entry: GaroConfigEntry,
    async_add_entities,
):
    """Set up using config_entry."""

    coordinator = entry.runtime_data.coordinator
    configuration = coordinator.config

    entities: list[NumberEntity] = []

    # Load-balancing meter 100
    if configuration.group_load_balanced:
        entities.extend([
            GaroLoadBalancingNumberEntity(
                coordinator,
                entry,
                GaroNumberEntityDescription(
                    key="load_balancing_current_100",
                    translation_key="load_balancing_current_100",
                    name="Meter 100 Current Limit",
                    icon="mdi:current-ac",
                    native_max_value=850,
                    native_min_value=16,
                    native_step=1,
                    native_unit_of_measurement="A",
                    mode=NumberMode.BOX,
                    get_value=lambda _: coordinator.load_balancing_fuse,
                    set_value=lambda value:
                        coordinator.async_set_load_balancing_value(
                            "loadBalancingFuse",
                            value,
                        ),
                    is_available=lambda: True,
                ),
            ),
            GaroLoadBalancingNumberEntity(
                coordinator,
                entry,
                GaroNumberEntityDescription(
                    key="load_balancing_power_100",
                    translation_key="load_balancing_power_100",
                    name="Meter 100 Power Limit",
                    icon="mdi:transmission-tower",
                    device_class=NumberDeviceClass.POWER,
                    native_max_value=250,
                    native_min_value=0,
                    native_step=1,
                    native_unit_of_measurement=UnitOfPower.KILO_WATT,
                    mode=NumberMode.BOX,
                    get_value=lambda _: coordinator.load_balancing_power,
                    set_value=lambda value:
                        coordinator.async_set_load_balancing_value(
                            "loadBalancingPower",
                            value,
                        ),
                    is_available=lambda: True,
                ),
            ),
        ])

    # Load-balancing meter 101
    if configuration.group_load_balanced101:
        entities.extend([
            GaroLoadBalancingNumberEntity(
                coordinator,
                entry,
                GaroNumberEntityDescription(
                    key="load_balancing_current_101",
                    translation_key="load_balancing_current_101",
                    name="Meter 101 Current Limit",
                    icon="mdi:current-ac",
                    native_max_value=850,
                    native_min_value=16,
                    native_step=1,
                    native_unit_of_measurement="A",
                    mode=NumberMode.BOX,
                    get_value=lambda _: coordinator.load_balancing_fuse101,
                    set_value=lambda value:
                        coordinator.async_set_load_balancing_value(
                            "loadBalancingFuse101",
                            value,
                        ),
                    is_available=lambda: True,
                ),
            ),
            GaroLoadBalancingNumberEntity(
                coordinator,
                entry,
                GaroNumberEntityDescription(
                    key="load_balancing_power_101",
                    translation_key="load_balancing_power_101",
                    name="Meter 101 Power Limit",
                    icon="mdi:transmission-tower",
                    device_class=NumberDeviceClass.POWER,
                    native_max_value=250,
                    native_min_value=0,
                    native_step=1,
                    native_unit_of_measurement=UnitOfPower.KILO_WATT,
                    mode=NumberMode.BOX,
                    get_value=lambda _: coordinator.load_balancing_power101,
                    set_value=lambda value:
                        coordinator.async_set_load_balancing_value(
                            "loadBalancingPower101",
                            value,
                        ),
                    is_available=lambda: True,
                ),
            ),
        ])

    # Existing energy-meter entities
    if entry.runtime_data.meter_coordinator:
        meter_coordinator = entry.runtime_data.meter_coordinator

        def add_meter_entities(meter: GaroMeter):
            entities.extend(
                GaroMeterNumberEntity(
                    meter_coordinator,
                    entry,
                    description,
                    meter,
                )
                for description in [
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
                        get_value=lambda status:
                            meter_coordinator.voltage,
                        set_value=lambda value:
                            meter_coordinator.async_set_voltage(value),
                        is_available=lambda: True,
                    )
                ]
            )

        if meter_coordinator.has_external_meter:
            add_meter_entities(meter_coordinator.external_meter)

        if meter_coordinator.has_central100_meter:
            add_meter_entities(meter_coordinator.central100_meter)

        if meter_coordinator.has_central101_meter:
            add_meter_entities(meter_coordinator.central101_meter)

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
class GaroLoadBalancingNumberEntity(GaroNumberEntity):

    def __init__(
        self,
        coordinator: GaroDeviceCoordinator,
        entry,
        description: GaroNumberEntityDescription,
    ):
        super().__init__(
            coordinator,
            entry,
            description,
        )

        self._attr_unique_id = (
            f"{coordinator.device_id}"
            f"-load_balancing-{description.key}"
        )

        self._attr_device_info = (
            coordinator.load_balancing_device_info
        )

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