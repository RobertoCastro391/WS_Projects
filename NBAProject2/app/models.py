from django.db import models

class QuizScore(models.Model):
    player_name = models.CharField(max_length=100)
    score = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.player_name} - {self.score}"
