from typing import Optional, Tuple
from datetime import date

from ..models import Employee, Department


class EmployeeNotFoundException(Exception):
    """Сотрудник не найден"""
    pass


class EmployeeValidationException(Exception):
    """Ошибка валидации сотрудника"""
    pass


class EmployeeService:
    """Сервис для работы с сотрудниками"""

    @staticmethod
    def validate_employee_data(
            full_name: str,
            position: str
    ) -> Tuple[bool, str]:
        """Валидация данных сотрудника"""
        errors = []

        # Валидация full_name
        if not full_name or not full_name.strip():
            errors.append("Full name cannot be empty")

        # Валидация position
        if not position or not position.strip():
            errors.append("Position cannot be empty")

        if errors:
            return False, ", ".join(errors)

        return True, ""

    @staticmethod
    def create_employee(
            department_id: int,
            full_name: str,
            position: str,
            hired_at: Optional[date] = None
    ) -> Employee:
        """Создание нового сотрудника"""
        # Валидация данных
        is_valid, error_message = EmployeeService.validate_employee_data(full_name, position)
        if not is_valid:
            raise EmployeeValidationException(error_message)

        # Очистка данных
        cleaned_full_name = full_name.strip()
        cleaned_position = position.strip()

        # Проверка длины
        if len(cleaned_full_name) > 200:
            raise EmployeeValidationException("Full name must be 200 characters or fewer")
        if len(cleaned_position) > 200:
            raise EmployeeValidationException("Position must be 200 characters or fewer")

        # Проверка существования отдела
        try:
            department = Department.objects.get(id=department_id)
        except Department.DoesNotExist:
            from .department_service import DepartmentNotFoundException
            raise DepartmentNotFoundException(f"Department with id {department_id} not found")

        try:
            employee = Employee.objects.create(
                department=department,
                full_name=cleaned_full_name,
                position=cleaned_position,
                hired_at=hired_at
            )
            return employee
        except Exception as e:
            raise EmployeeValidationException(str(e))

    @staticmethod
    def reassign_employees(
            from_department: Department,
            to_department: Department
    ) -> None:
        """Перенос сотрудников из одного отдела в другой"""
        Employee.objects.filter(department=from_department).update(
            department=to_department
        )

    @staticmethod
    def get_employee(employee_id: int) -> Employee:
        """Получение сотрудника по ID"""
        try:
            return Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            raise EmployeeNotFoundException(f"Employee with id {employee_id} not found")