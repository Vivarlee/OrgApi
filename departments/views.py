from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from pydantic import ValidationError as PydanticValidationError

from .services.department_service import (
    DepartmentService,
    DepartmentNotFoundException,
    DepartmentValidationException,
    DepartmentCircularReferenceException,
)
from .services.employee_service import (
    EmployeeService,
    EmployeeNotFoundException,
    EmployeeValidationException,
)
from .schemas import (
    DepartmentCreate,
    DepartmentUpdate,
    EmployeeCreate,
    DepartmentResponse,
    EmployeeResponse,
)


@api_view(['POST'])
def create_department(request):
    """Создание нового отдела"""
    try:
        data = DepartmentCreate(**request.data)
    except (PydanticValidationError, ValueError, Exception) as e:
        return _handle_pydantic_error(e)

    try:
        department = DepartmentService.create_department(
            name=data.name,
            parent_id=data.parent_id
        )
        response_data = DepartmentResponse.from_orm(department)
        return Response(response_data.dict(), status=status.HTTP_201_CREATED)
    except DepartmentNotFoundException as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
    except DepartmentValidationException as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def create_employee(request, id):
    """Создание нового сотрудника"""
    try:
        data = EmployeeCreate(**request.data)
    except (PydanticValidationError, ValueError, Exception) as e:
        return _handle_pydantic_error(e)

    try:
        employee = EmployeeService.create_employee(
            department_id=id,
            full_name=data.full_name,
            position=data.position,
            hired_at=data.hired_at
        )
        response_data = EmployeeResponse.from_orm(employee)
        return Response(response_data.dict(), status=status.HTTP_201_CREATED)
    except DepartmentNotFoundException as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
    except EmployeeValidationException as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
def department_detail(request, id):
    """Обработка GET, PATCH и DELETE запросов для отдела"""
    if request.method == 'GET':
        return get_department(request, id)
    elif request.method == 'PATCH':
        return update_department(request, id)
    elif request.method == 'DELETE':
        return delete_department(request, id)


def get_department(request, id):
    """Получение информации об отделе"""
    try:
        depth = int(request.query_params.get('depth', 1))
    except ValueError:
        depth = 1

    include_employees = request.query_params.get('include_employees', 'true').lower() == 'true'

    # Валидация depth
    depth = max(1, min(depth, 5))

    try:
        department_tree = DepartmentService.get_department_tree(
            department_id=id,
            depth=depth,
            include_employees=include_employees
        )
        return Response(department_tree.dict())
    except DepartmentNotFoundException as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


def update_department(request, id):
    """Обновление отдела"""
    try:
        data = DepartmentUpdate(**request.data)
    except (PydanticValidationError, ValueError, Exception) as e:
        return _handle_pydantic_error(e)

    try:
        department = DepartmentService.update_department(
            department_id=id,
            name=data.name,
            parent_id=data.parent_id
        )
        response_data = DepartmentResponse.from_orm(department)
        return Response(response_data.dict())
    except DepartmentNotFoundException as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
    except DepartmentCircularReferenceException as e:
        return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
    except DepartmentValidationException as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


def delete_department(request, id):
    """Удаление отдела"""
    mode = request.query_params.get('mode', 'cascade')

    if mode not in ['cascade', 'reassign']:
        return Response(
            {'error': 'Mode must be "cascade" or "reassign"'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        if mode == 'cascade':
            DepartmentService.delete_department_cascade(department_id=id)
        else:  # reassign
            reassign_to_id = request.query_params.get('reassign_to_department_id')
            if not reassign_to_id:
                return Response(
                    {'error': 'reassign_to_department_id is required when mode=reassign'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            DepartmentService.delete_department_reassign(
                department_id=id,
                reassign_to_id=int(reassign_to_id)
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
    except DepartmentNotFoundException as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
    except DepartmentCircularReferenceException as e:
        return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


def _handle_pydantic_error(e: Exception) -> Response:
    """Обработка ошибок Pydantic"""
    error_msg = str(e)
    if hasattr(e, 'errors'):
        error_msg = str(e.errors())
    return Response(
        {'error': 'Validation error', 'details': error_msg},
        status=status.HTTP_400_BAD_REQUEST
    )