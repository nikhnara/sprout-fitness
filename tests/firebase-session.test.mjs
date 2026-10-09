import {test} from 'node:test';
import assert from 'node:assert/strict';
import {sessionFromSdk} from '../dist/firebase-session.mjs';
test('each API token request delegates refresh to Firebase and refuses signed-out access',async()=>{
 let requests=0;
 const auth={currentUser:{getIdToken:async()=>`fresh-${++requests}`}};
 const sdk={onAuthStateChanged:()=>()=>{}};
 const session=sessionFromSdk(auth,sdk,()=>{});
 assert.equal(await session.idToken(),'fresh-1');assert.equal(await session.idToken(),'fresh-2');
 auth.currentUser=null;await assert.rejects(session.idToken(),/Sign in/);
});
test('sign-out and session changes are handled by Firebase',async()=>{
 const auth={currentUser:{uid:'owner'}};let observed;
 const sdk={onAuthStateChanged(a,callback){observed=callback;return ()=>{};},async signOut(a){a.currentUser=null;observed(null);}};
 let user='initial';const session=sessionFromSdk(auth,sdk,u=>user=u);
 await session.signOut();assert.equal(user,null);await assert.rejects(session.idToken());
});
