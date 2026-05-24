from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError as DjangoValidationError
from pydantic import ValidationError as PydanticValidationError

from .models import Department, Employee
from .schemas import (
    DepartmentCreate,
    DepartmentUpdate,
    EmployeeCreate,
    DepartmentResponse,
    EmployeeResponse,
    DepartmentTreeResponse,
)


@api_view(['POST'])
def create_department(request):
    """Create a new department"""
    try:
        data = DepartmentCreate(**request.data)
    except (PydanticValidationError, ValueError, Exception) as e:
        error_msg = str(e)
        if hasattr(e, 'errors'):
            error_msg = str(e.errors())
        return Response(
            {'error': 'Validation error', 'details': error_msg},
            status=status.HTTP_400_BAD_REQUEST
        )

    parent = None
    if data.parent_id:
        try:
            parent = Department.objects.get(id=data.parent_id)
        except Department.DoesNotExist:
            return Response(
                {'error': f'Parent department with id {data.parent_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    try:
        department = Department(name=data.name, parent=parent)
        department.full_clean()
        department.save()
    except DjangoValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except IntegrityError:
        return Response(
            {'error': 'Department with this name already exists under the same parent'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

    response_data = DepartmentResponse.from_orm(department)
    return Response(response_data.dict(), status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
def department_detail(request, id):
    """Handle GET, PATCH, and DELETE for a specific department"""
    if request.method == 'GET':
        return get_department(request, id)
    elif request.method == 'PATCH':
        return update_department(request, id)
    elif request.method == 'DELETE':
        return delete_department(request, id)


@api_view(['POST'])
def create_employee(request, id):
    """Create a new employee in a department"""
    try:
        data = EmployeeCreate(**request.data)
    except (PydanticValidationError, ValueError, Exception) as e:
        error_msg = str(e)
        if hasattr(e, 'errors'):
            error_msg = str(e.errors())
        return Response(
            {'error': 'Validation error', 'details': error_msg},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        department = Department.objects.get(id=id)
    except Department.DoesNotExist:
        return Response(
            {'error': f'Department with id {id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        employee = Employee(
            department=department,
            full_name=data.full_name,
            position=data.position,
            hired_at=data.hired_at
        )
        employee.full_clean()
        employee.save()
    except DjangoValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

    response_data = EmployeeResponse.from_orm(employee)
    return Response(response_data.dict(), status=status.HTTP_201_CREATED)


def get_department(request, id):
    """Get department details with employees and subtree"""
    try:
        depth = int(request.query_params.get('depth', 1))
    except ValueError:
        depth = 1

    include_employees = request.query_params.get('include_employees', 'true').lower() == 'true'

    # Validate depth
    if depth < 1:
        depth = 1
    elif depth > 5:
        depth = 5

    try:
        department = Department.objects.get(id=id)
    except Department.DoesNotExist:
        return Response(
            {'error': f'Department with id {id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    response_data = build_department_tree(department, depth, include_employees)
    return Response(response_data.dict())


def build_department_tree(department, depth, include_employees, current_depth=1):
    """Recursively build department tree"""
    employees = None
    if include_employees:
        employees = [
            EmployeeResponse.from_orm(emp)
            for emp in department.employees.all().order_by('created_at', 'full_name')
        ]

    children = None
    if current_depth < depth:
        children_deps = department.children.all()
        if children_deps:
            children = [
                build_department_tree(child, depth, include_employees, current_depth + 1)
                for child in children_deps
            ]

    return DepartmentTreeResponse(
        id=department.id,
        name=department.name,
        parent_id=department.parent_id,
        created_at=department.created_at,
        employees=employees,
        children=children
    )


def update_department(request, id):
    """Update department (name and/or parent)"""
    try:
        data = DepartmentUpdate(**request.data)
    except (PydanticValidationError, ValueError, Exception) as e:
        error_msg = str(e)
        if hasattr(e, 'errors'):
            error_msg = str(e.errors())
        return Response(
            {'error': 'Validation error', 'details': error_msg},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        department = Department.objects.get(id=id)
    except Department.DoesNotExist:
        return Response(
            {'error': f'Department with id {id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Update name if provided
    if data.name is not None:
        department.name = data.name

    # Update parent if provided
    if data.parent_id is not None:
        if data.parent_id == department.id:
            return Response(
                {'error': 'Department cannot be its own parent'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if data.parent_id:
            try:
                new_parent = Department.objects.get(id=data.parent_id)
            except Department.DoesNotExist:
                return Response(
                    {'error': f'Parent department with id {data.parent_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check for circular reference
            if department.is_ancestor_of(new_parent) or department.id == new_parent.id:
                return Response(
                    {'error': 'Cannot create circular reference in department tree'},
                    status=status.HTTP_409_CONFLICT
                )
        else:
            new_parent = None

        department.parent = new_parent

    try:
        department.full_clean()
        department.save()
    except DjangoValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except IntegrityError:
        return Response(
            {'error': 'Department with this name already exists under the same parent'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

    response_data = DepartmentResponse.from_orm(department)
    return Response(response_data.dict())


def delete_department(request, id):
    """Delete department with cascade or reassign mode"""
    mode = request.query_params.get('mode', 'cascade')

    if mode not in ['cascade', 'reassign']:
        return Response(
            {'error': 'Mode must be "cascade" or "reassign"'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        department = Department.objects.get(id=id)
    except Department.DoesNotExist:
        return Response(
            {'error': f'Department with id {id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if mode == 'reassign':
        reassign_to_id = request.query_params.get('reassign_to_department_id')
        if not reassign_to_id:
            return Response(
                {'error': 'reassign_to_department_id is required when mode=reassign'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            reassign_to = Department.objects.get(id=reassign_to_id)
        except Department.DoesNotExist:
            return Response(
                {'error': f'Target department with id {reassign_to_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check for circular reference
        if department.is_ancestor_of(reassign_to) or department.id == reassign_to.id:
            return Response(
                {'error': 'Cannot reassign to department that would create circular reference'},
                status=status.HTTP_409_CONFLICT
            )

        with transaction.atomic():
            # Move all employees to new department
            Employee.objects.filter(department=department).update(
                department=reassign_to
            )
            # Move child departments to new parent
            for child in department.children.all():
                child.parent = reassign_to
                child.save()
            # Delete the department
            department.delete()

    else:  # cascade mode
        # Django's CASCADE will handle this automatically
        department.delete()

    return Response(status=status.HTTP_204_NO_CONTENT)