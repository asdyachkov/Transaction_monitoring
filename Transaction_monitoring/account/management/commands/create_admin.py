from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Создает администратора с логином и паролем "admin"'

    def handle(self, *args, **kwargs):
        User = get_user_model()

        # Проверка на существование пользователя с логином "admin"
        if not User.objects.filter(username='admin').exists():
            try:
                # Создание суперпользователя с фиксированными данными
                User.objects.create_superuser(
                    username='admin',
                    email='example@admin.com',
                    password='admin',
                    phone_number='89999999999'
                )
                self.stdout.write(self.style.SUCCESS('Администратор успешно создан: admin/admin'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Ошибка при создании администратора: {str(e)}'))
        else:
            self.stdout.write(self.style.WARNING('Администратор с логином "admin" уже существует'))
