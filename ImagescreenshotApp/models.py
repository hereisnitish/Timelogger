from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import User

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    stop_screenshots = models.BooleanField(default=False)
    pause_screenshots = models.BooleanField(default=False)
    

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.username

class Image(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='screenshots/')
    date_taken = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Screenshot for {self.user.username} at {self.date_taken}"
    
class DailyTimestamp(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    time = models.TimeField()

    def __str__(self):
        return f"{self.user.username} - {self.date} {self.time}"

    class Meta:
        unique_together = ['user', 'date']

class FaceCapture(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='face_captures/')
    date_taken = models.DateTimeField(auto_now_add=True)

class activityIntensity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    key_count = models.IntegerField(default=0)
    mouse_count = models.IntegerField(default=0)
    activity_intensity = models.IntegerField(default=0)
