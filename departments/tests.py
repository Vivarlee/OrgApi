from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import Department, Employee
import json


class DepartmentAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.department_data = {'name': 'Engineering'}
        self.employee_data = {
            'full_name': 'John Doe',
            'position': 'Developer',
            'hired_at': '2024-01-15'
        }

    def test_create_department(self):
        """Test creating a department"""
        response = self.client.post(
            '/departments/',
            data=json.dumps(self.department_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Engineering')
        self.assertIsNone(response.data['parent_id'])

    def test_create_department_with_parent(self):
        """Test creating a department with parent"""
        parent = Department.objects.create(name='Parent Dept')
        response = self.client.post(
            '/departments/',
            data=json.dumps({'name': 'Child Dept', 'parent_id': parent.id}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['parent_id'], parent.id)

    def test_create_department_empty_name(self):
        """Test creating a department with empty name"""
        response = self.client.post(
            '/departments/',
            data=json.dumps({'name': '   '}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_employee(self):
        """Test creating an employee"""
        department = Department.objects.create(name='Engineering')
        response = self.client.post(
            f'/departments/{department.id}/employees/',
            data=json.dumps(self.employee_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['full_name'], 'John Doe')
        self.assertEqual(response.data['position'], 'Developer')

    def test_create_employee_invalid_department(self):
        """Test creating employee in non-existent department"""
        response = self.client.post(
            '/departments/999/employees/',
            data=json.dumps(self.employee_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_department_tree(self):
        """Test getting department tree with employees and children"""
        parent = Department.objects.create(name='Parent')
        child = Department.objects.create(name='Child', parent=parent)
        Employee.objects.create(
            department=parent,
            full_name='John Doe',
            position='Developer'
        )

        response = self.client.get(
            f'/departments/{parent.id}/?depth=2&include_employees=true'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Parent')
        self.assertEqual(len(response.data['employees']), 1)
        self.assertEqual(len(response.data['children']), 1)
        self.assertEqual(response.data['children'][0]['name'], 'Child')

    def test_update_department_parent(self):
        """Test updating department parent"""
        parent1 = Department.objects.create(name='Parent 1')
        parent2 = Department.objects.create(name='Parent 2')
        child = Department.objects.create(name='Child', parent=parent1)

        response = self.client.patch(
            f'/departments/{child.id}/',
            data=json.dumps({'parent_id': parent2.id}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        child.refresh_from_db()
        self.assertEqual(child.parent, parent2)

    def test_prevent_circular_reference(self):
        """Test preventing circular reference in department tree"""
        parent = Department.objects.create(name='Parent')
        child = Department.objects.create(name='Child', parent=parent)

        response = self.client.patch(
            f'/departments/{parent.id}/',
            data=json.dumps({'parent_id': child.id}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_delete_department_cascade(self):
        """Test cascade deletion of department"""
        department = Department.objects.create(name='To Delete')
        Employee.objects.create(
            department=department,
            full_name='Jane Doe',
            position='Manager'
        )

        response = self.client.delete(
            f'/departments/{department.id}/?mode=cascade'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Department.objects.count(), 0)
        self.assertEqual(Employee.objects.count(), 0)

    def test_delete_department_reassign(self):
        """Test reassign deletion of department"""
        source_dept = Department.objects.create(name='Source')
        target_dept = Department.objects.create(name='Target')
        employee = Employee.objects.create(
            department=source_dept,
            full_name='Jane Doe',
            position='Manager'
        )

        response = self.client.delete(
            f'/departments/{source_dept.id}/'
            f'?mode=reassign&reassign_to_department_id={target_dept.id}'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Department.objects.filter(id=source_dept.id).exists())
        employee.refresh_from_db()
        self.assertEqual(employee.department, target_dept)

    def test_unique_department_name_per_parent(self):
        """Test unique department name constraint"""
        parent = Department.objects.create(name='Parent')
        Department.objects.create(name='Child', parent=parent)

        response = self.client.post(
            '/departments/',
            data=json.dumps({'name': 'Child', 'parent_id': parent.id}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)