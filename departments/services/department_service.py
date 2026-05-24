from typing import Optional, List, Tuple
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError as DjangoValidationError

from ..models import Department, Employee
from ..schemas import DepartmentTreeResponse, EmployeeResponse


class DepartmentNotFoundException(Exception):
    """Отдел не найден"""
    pass


class DepartmentValidationException(Exception):
    """Ошибка валидации отдела"""
    pass


class DepartmentCircularReferenceException(Exception):
    """Циклическая ссылка в дереве отделов"""
    pass


class DepartmentService:
    """Сервис для работы с отделами"""

    @staticmethod
    def is_ancestor_of(ancestor: Department, descendant: Department) -> bool:
        """
        Проверяет, является ли ancestor предком descendant

        Args:
            ancestor: Предполагаемый предок
            descendant: Предполагаемый потомок

        Returns:
            bool: True если ancestor является предком descendant
        """
        if not descendant or not descendant.parent_id:
            return False

        # Проверяем цепочку родителей
        current = descendant.parent
        visited = set()  # Защита от бесконечного цикла

        while current:
            if current.id in visited:
                break
            visited.add(current.id)

            if current.id == ancestor.id:
                return True
            current = current.parent

        return False

    @staticmethod
    def validate_name(name: str) -> Tuple[bool, str]:
        """Валидация названия отдела"""
        if not name or not name.strip():
            return False, "Name cannot be empty"

        name = name.strip()
        if len(name) > 200:
            return False, "Name must be 200 characters or fewer"

        return True, name

    @staticmethod
    def create_department(name: str, parent_id: Optional[int] = None) -> Department:
        """Создание нового отдела"""
        # Валидация имени
        is_valid, result = DepartmentService.validate_name(name)
        if not is_valid:
            raise DepartmentValidationException(result)

        cleaned_name = result

        # Проверка родительского отдела
        parent = None
        if parent_id:
            try:
                parent = Department.objects.get(id=parent_id)
            except Department.DoesNotExist:
                raise DepartmentNotFoundException(f"Parent department with id {parent_id} not found")

        try:
            department = Department.objects.create(
                name=cleaned_name,
                parent=parent
            )
            return department
        except IntegrityError:
            raise DepartmentValidationException(
                "Department with this name already exists under the same parent"
            )

    @staticmethod
    def update_department(
            department_id: int,
            name: Optional[str] = None,
            parent_id: Optional[int] = None
    ) -> Department:
        """Обновление отдела"""
        try:
            department = Department.objects.get(id=department_id)
        except Department.DoesNotExist:
            raise DepartmentNotFoundException(f"Department with id {department_id} not found")

        # Обновление имени
        if name is not None:
            is_valid, result = DepartmentService.validate_name(name)
            if not is_valid:
                raise DepartmentValidationException(result)
            department.name = result

        # Обновление родителя
        if parent_id is not None:
            if parent_id == department.id:
                raise DepartmentCircularReferenceException("Department cannot be its own parent")

            if parent_id:
                try:
                    new_parent = Department.objects.get(id=parent_id)
                except Department.DoesNotExist:
                    raise DepartmentNotFoundException(f"Parent department with id {parent_id} not found")

                # Проверка на циклическую ссылку
                if DepartmentService.is_ancestor_of(department, new_parent) or department.id == new_parent.id:
                    raise DepartmentCircularReferenceException(
                        "Cannot create circular reference in department tree"
                    )

                department.parent = new_parent
            else:
                department.parent = None

        try:
            department.save()
            return department
        except IntegrityError:
            raise DepartmentValidationException(
                "Department with this name already exists under the same parent"
            )

    @staticmethod
    def get_department_tree(
            department_id: int,
            depth: int = 1,
            include_employees: bool = True
    ) -> DepartmentTreeResponse:
        """Получение дерева отдела с сотрудниками и подотделами"""
        try:
            department = Department.objects.get(id=department_id)
        except Department.DoesNotExist:
            raise DepartmentNotFoundException(f"Department with id {department_id} not found")

        return DepartmentService._build_tree(department, depth, include_employees)

    @staticmethod
    def _build_tree(
            department: Department,
            depth: int,
            include_employees: bool,
            current_depth: int = 1
    ) -> DepartmentTreeResponse:
        """Рекурсивное построение дерева отделов"""
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
                    DepartmentService._build_tree(child, depth, include_employees, current_depth + 1)
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

    @staticmethod
    def delete_department_cascade(department_id: int) -> None:
        """Каскадное удаление отдела"""
        try:
            department = Department.objects.get(id=department_id)
        except Department.DoesNotExist:
            raise DepartmentNotFoundException(f"Department with id {department_id} not found")

        department.delete()

    @staticmethod
    def delete_department_reassign(department_id: int, reassign_to_id: int) -> None:
        """Удаление отдела с переносом сотрудников"""
        try:
            department = Department.objects.get(id=department_id)
        except Department.DoesNotExist:
            raise DepartmentNotFoundException(f"Department with id {department_id} not found")

        try:
            reassign_to = Department.objects.get(id=reassign_to_id)
        except Department.DoesNotExist:
            raise DepartmentNotFoundException(f"Target department with id {reassign_to_id} not found")

        # Проверка на циклическую ссылку
        if DepartmentService.is_ancestor_of(department, reassign_to) or department.id == reassign_to.id:
            raise DepartmentCircularReferenceException(
                "Cannot reassign to department that would create circular reference"
            )

        with transaction.atomic():
            # Перенос сотрудников
            Employee.objects.filter(department=department).update(
                department=reassign_to
            )

            # Перенос дочерних отделов
            for child in department.children.all():
                child.parent = reassign_to
                child.save()

            # Удаление отдела
            department.delete()

    @staticmethod
    def get_all_descendants(department: Department) -> List[Department]:
        """
        Получить всех потомков отдела (рекурсивно)

        Args:
            department: Отдел

        Returns:
            List[Department]: Список всех дочерних отделов на всех уровнях
        """
        descendants = []
        children = department.children.all()

        for child in children:
            descendants.append(child)
            descendants.extend(DepartmentService.get_all_descendants(child))

        return descendants

    @staticmethod
    def get_ancestors(department: Department) -> List[Department]:
        """
        Получить всех предков отдела

        Args:
            department: Отдел

        Returns:
            List[Department]: Список родительских отделов до корня
        """
        ancestors = []
        current = department.parent

        while current:
            ancestors.append(current)
            current = current.parent

        return ancestors

    @staticmethod
    def can_move_department(department: Department, new_parent: Optional[Department]) -> bool:
        """
        Проверить, можно ли переместить отдел к новому родителю

        Args:
            department: Перемещаемый отдел
            new_parent: Новый родитель (None для корневого уровня)

        Returns:
            bool: True если перемещение возможно
        """
        if not new_parent:
            return True

        # Нельзя сделать отдел родителем самого себя
        if department.id == new_parent.id:
            return False

        # Нельзя создать циклическую ссылку
        if DepartmentService.is_ancestor_of(department, new_parent):
            return False

        return True