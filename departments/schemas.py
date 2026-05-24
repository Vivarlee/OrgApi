from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime


def validate_not_empty(v: str, field_name: str) -> str:
    """Validate that a string is not empty after stripping"""
    if not isinstance(v, str):
        raise ValueError(f'{field_name} must be a string')
    v = v.strip()
    if not v:
        raise ValueError(f'{field_name} cannot be empty')
    if len(v) > 200:
        raise ValueError(f'{field_name} must be 200 characters or fewer')
    return v


class DepartmentCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None

    @validator('name')
    def validate_name(cls, v):
        return validate_not_empty(v, 'Name')


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None

    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            return validate_not_empty(v, 'Name')
        return v


class EmployeeCreate(BaseModel):
    full_name: str
    position: str
    hired_at: Optional[date] = None

    @validator('full_name')
    def validate_full_name(cls, v):
        return validate_not_empty(v, 'Full name')

    @validator('position')
    def validate_position(cls, v):
        return validate_not_empty(v, 'Position')


class DepartmentResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EmployeeResponse(BaseModel):
    id: int
    department_id: int
    full_name: str
    position: str
    hired_at: Optional[date] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DepartmentTreeResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    created_at: datetime
    employees: Optional[List[EmployeeResponse]] = None
    children: Optional[List['DepartmentTreeResponse']] = None

    class Config:
        from_attributes = True