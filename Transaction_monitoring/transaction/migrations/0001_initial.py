# Generated by Django 4.2.14 on 2024-07-25 19:53

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('account', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=20)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')], max_length=20)),
                ('description', models.TextField(blank=True, null=True)),
                ('receiver_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_transactions', to='account.account')),
                ('sender_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_transactions', to='account.account')),
            ],
        ),
    ]
