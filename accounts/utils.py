from accounts.models import UserPermission


def get_permissions(user):
    from collections import defaultdict
    permissions = UserPermission.objects.filter(user=user).values('module', 'action')

    # Transform into desired format
    result = defaultdict(list)
    for perm in permissions:
        result[perm['module']].append(perm['action'])


    normalized = {
        'seats': result.get('seat', []),
        'badges': result.get('badge', []),
        'users': result.get('user', []),
        'alignment': result.get('align', []),
    }

    print('-----normalized-permission------', normalized)
    return normalized
