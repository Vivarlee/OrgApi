from django.db import models
from django.core.exceptions import ValidationError


class Department(models.Model):
    name = models.CharField(max_length=200)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'parent'],
                name='unique_name_per_parent'
            )
        ]

    def clean(self):
        if self.name:
            self.name = self.name.strip()
        if not self.name:
            raise ValidationError({'name': 'Name cannot be empty'})
        if len(self.name) > 200:
            raise ValidationError({'name': 'Name must be 200 characters or fewer'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def is_ancestor_of(self, department):
        """Check if this department is an ancestor of the given department"""
        if not department or not department.parent:
            return False

        current = department.parent
        visited = set()

        while current:
            if current.id in visited:
                # Circular reference detected, break to avoid infinite loop
                break
            visited.add(current.id)

            if current.id == self.id:
                return True
            current = current.parent

        return False


class Employee(models.Model):
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='employees'
    )
    full_name = models.CharField(max_length=200)
    position = models.CharField(max_length=200)
    hired_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def clean(self):
        if self.full_name:
            self.full_name = self.full_name.strip()
        if self.position:
            self.position = self.position.strip()

        if not self.full_name:
            raise ValidationError({'full_name': 'Full name cannot be empty'})
        if not self.position:
            raise ValidationError({'position': 'Position cannot be empty'})
        if len(self.full_name) > 200:
            raise ValidationError({'full_name': 'Full name must be 200 characters or fewer'})
        if len(self.position) > 200:
            raise ValidationError({'position': 'Position must be 200 characters or fewer'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} - {self.position}"