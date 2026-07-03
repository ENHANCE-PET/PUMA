"""Display presets for PUMA PET multiplexing."""

from __future__ import annotations

from dataclasses import dataclass


CHANNELS = ("R", "G", "B")


@dataclass(frozen=True)
class DisplayPreset:
    name: str
    description: str
    mode: str = "adaptive"
    window_low: float = 2.0
    window_high: float = 99.7
    balance: str = "mean"
    weights: dict[str, float] | None = None
    gammas: dict[str, float] | None = None
    blackpoints: dict[str, float] | None = None

    def channel_weights(self) -> dict[str, float]:
        return _with_defaults(self.weights, 1.0)

    def channel_gammas(self) -> dict[str, float]:
        return _with_defaults(self.gammas, 0.85)

    def channel_blackpoints(self) -> dict[str, float]:
        return _with_defaults(self.blackpoints, 0.0)


def _with_defaults(values: dict[str, float] | None, default: float) -> dict[str, float]:
    result = {channel: default for channel in CHANNELS}
    if values:
        result.update({channel.upper(): value for channel, value in values.items()})
    return result


DISPLAY_PRESETS = {
    "legacy": DisplayPreset(
        name="legacy",
        description="Original PUMA min-max RGB mapping.",
        mode="legacy",
    ),
    "balanced": DisplayPreset(
        name="balanced",
        description="Adaptive per-tracer foreground windows with balanced RGB contribution.",
        balance="mean",
    ),
    "green-suppressed": DisplayPreset(
        name="green-suppressed",
        description="Adaptive display with restrained green channel for DOTATE/PSMA-dominant studies.",
        balance="mean",
        weights={"R": 1.20, "G": 0.65},
    ),
    "red-focus": DisplayPreset(
        name="red-focus",
        description="Adaptive display emphasizing red-channel hotspot conspicuity.",
        balance="none",
        weights={"R": 1.55, "G": 0.65},
        gammas={"R": 1.20, "G": 0.85, "B": 0.85},
        blackpoints={"R": 0.04},
    ),
}


GALLERY_PRESETS = ("balanced", "green-suppressed", "red-focus")


def get_display_preset(name: str) -> DisplayPreset:
    try:
        return DISPLAY_PRESETS[name]
    except KeyError as exc:
        choices = ", ".join(DISPLAY_PRESETS)
        raise ValueError(f"Unknown display preset '{name}'. Choices: {choices}") from exc
