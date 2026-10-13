"""Public-safe scene configuration models for the CAD training client."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Vector3 = tuple[float, float, float]


class CameraConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    position: Vector3
    target: Vector3
    zoom: float = Field(gt=0)


class WorkcellConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    robot_origin: Vector3
    workpiece_position: Vector3
    target_position: Vector3


class AnimationStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9-]*$")
    label: str = Field(min_length=1)
    duration_ms: int = Field(ge=100, le=30_000)
    status: Literal[
        "READY",
        "EXECUTING",
        "GRASP_ATTEMPT",
        "FAILURE_OBSERVED",
    ]
    joint_angles: tuple[float, float, float, float]
    gripper_opening: float = Field(ge=0, le=1)
    object_attached: bool


class SceneConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(pattern=r"^ST-[0-9]{3}$")
    version: str = Field(min_length=1)
    title: str = Field(min_length=1)
    task: str = Field(min_length=1)
    camera: CameraConfiguration
    workcell: WorkcellConfiguration
    timeline: tuple[AnimationStep, ...] = Field(min_length=2)
    public_observations: tuple[str, ...] = Field(min_length=1)
