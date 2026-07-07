from rest_framework import permissions

class IsSuperAdmin(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff


class IsCompanyManagerOrSuperAdmin(permissions.BasePermission):
    
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        
        user_company_id = getattr(request.user, 'company_id', None)
        if user_company_id is None:
            return False
            
        if hasattr(obj, 'company_id'):
            return obj.company_id == user_company_id
        if hasattr(obj, 'company'):
            return obj.company_id == user_company_id
        return False
    