from django.db import models

from account.models import Account
from django.utils.timezone import now


class Transaction(models.Model):
    sender_account = models.ForeignKey(Account, related_name='sent_transactions', on_delete=models.CASCADE)
    receiver_account = models.ForeignKey(Account, related_name='received_transactions', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    timestamp = models.DateTimeField(default=now, blank=False, null=False)
    type = models.CharField(max_length=50, default="transfer")
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')], default='Pending')
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.sender_account} -> {self.receiver_account} : {self.amount} {self.sender_account.currency.code}"
