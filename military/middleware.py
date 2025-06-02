#from django.http import JsonResponse
#import redis
#from military_division import settings

#class RedisAuthMiddleware:
 #   def __init__(self, get_response):
  #      self.get_response = get_response
   #     self.redis_client = redis.Redis(
    #        host=settings.REDIS_HOST,
     #       port=settings.REDIS_PORT,
      #      db=settings.REDIS_DB
        #)

    #def __call__(self, request):
     #   if not request.user.is_authenticated:
      #      token = request.COOKIES.get('auth_token')
       #     if token:
        #        user_id = self.redis_client.get(f'token:{token}')
         #       if user_id:
          #          from django.contrib.auth import get_user_model
           #         User = get_user_model()
            #        request.user = User.objects.get(id=int(user_id))

#        response = self.get_response(request)
 #       return response