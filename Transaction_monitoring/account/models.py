from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.timezone import now
from currency.models import Currency


class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    language_preference = models.CharField(max_length=50, default='eng')
    frequent_countries = models.JSONField(default=list, null=True, blank=True)
    frequent_transaction_types = models.JSONField(default=list, null=True, blank=True)
    average_transaction_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_transaction_amount = models.DecimalField(max_digits=10, decimal_places=2, default=10000)
    unusual_time_hour_start = models.IntegerField(default=0)
    unusual_time_hour_end = models.IntegerField(default=23)
    max_transactions_per_hour = models.IntegerField(default=10)
    suspicious_countries = models.JSONField(default=list, null=True, blank=True)

    def __str__(self):
        return self.user.username

    def update_profile(self, transaction, country):
        if transaction['ip']:
            if country not in self.frequent_countries:
                self.frequent_countries.append(country)
        if transaction['type']:
            if transaction['type'] not in self.frequent_transaction_types:
                self.frequent_transaction_types.append(transaction['type'])
        self.save()


class Account(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.user.username} - {self.currency.code}"
