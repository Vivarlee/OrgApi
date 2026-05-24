from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: Optional[int] = None

    @validator('name')
    def validate_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('Name cannot be empty')
        if len(v) > 200:
            raise ValueError('Name must be 200 characters or fewer')
        return v


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    parent_id: Optional[int] = None

    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('Name cannot be empty')
            if len(v) > 200:
                raise ValueError('Name must be 200 characters or fewer')
        return v


class EmployeeCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    position: str = Field(..., min_length=1, max_length=200)
    hired_at: Optional[date] = None

    @validator('full_name')
    def validate_full_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('Full name cannot be empty')
        return v

    @validator('position')
    def validate_position(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('Position cannot be empty')
        return v


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