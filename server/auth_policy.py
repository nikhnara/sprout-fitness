"""Authorization follows Firebase signature/project/expiry verification."""
import hashlib

def owner_from_bearer(header, owner_email, verify):
    if not isinstance(header, str) or not header.startswith('Bearer '):
        raise ValueError('A Firebase bearer token is required.')
    token = header[len('Bearer '):]
    if not token or any(c.isspace() for c in token):
        raise ValueError('Invalid bearer token.')
    claims = verify(token)
    if (claims.get('email_verified') is not True
            or not owner_email
            or claims.get('email', '').casefold() != owner_email.casefold()
            or claims.get('firebase', {}).get('sign_in_provider') != 'google.com'):
        raise ValueError('Sign in with the owner Google account.')
    uid = claims.get('uid')
    if not isinstance(uid, str) or not uid:
        raise ValueError('Firebase user ID is required.')
    return hashlib.sha256(uid.encode()).hexdigest()
