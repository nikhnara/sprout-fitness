// Firebase manages session persistence and refresh. Never store bearer tokens in diary JSON.
export function sessionFromSdk(auth,sdk,onChange){
 const unsubscribe=sdk.onAuthStateChanged(auth,onChange);
 return {
  signIn(){const provider=new sdk.GoogleAuthProvider();provider.setCustomParameters({prompt:'select_account'});return sdk.signInWithPopup(auth,provider);},
  signOut(){return sdk.signOut(auth);},
  async idToken(){const user=auth.currentUser;if(!user)throw Error('Sign in before syncing your diary.');return user.getIdToken();},
  dispose:unsubscribe
 };
}
export async function createFirebaseSession(config,onChange){
 const [appSdk,authSdk]=await Promise.all([
  import('https://www.gstatic.com/firebasejs/13.0.0/firebase-app.js'),
  import('https://www.gstatic.com/firebasejs/13.0.0/firebase-auth.js')
 ]);
 const app=appSdk.initializeApp(config,'sprout');
 const auth=authSdk.getAuth(app);
 await authSdk.setPersistence(auth,authSdk.browserLocalPersistence);
 return sessionFromSdk(auth,authSdk,onChange);
}
