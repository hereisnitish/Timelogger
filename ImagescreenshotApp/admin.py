from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(Image)
admin.site.register(DailyTimestamp)
admin.site.register(FaceCapture)
admin.site.register(User)
admin.site.register(activityIntensity)

