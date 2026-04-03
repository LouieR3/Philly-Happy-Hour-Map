// ── Firebase client-side auth ─────────────────────────────────────────────────
// Uses the Firebase JS SDK (loaded via CDN in index.html as ES modules).
// This file is loaded as type="module".

import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js';
import {
  getAuth,
  signInWithPopup,
  signOut,
  onAuthStateChanged,
  GoogleAuthProvider,
} from 'https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js';

// ── Replace these values with your Firebase project's web app config ──────────
// Firebase Console → Project Settings → Your apps → Web app → Config snippet
const firebaseConfig = {
  apiKey:            "AIzaSyAK2bb2zN7ibRWsgc7SSU5ibUOHwpbksEI",
  authDomain:        "mappy-hour-39fb6.firebaseapp.com",
  projectId:         "mappy-hour-39fb6",
  storageBucket:     "mappy-hour-39fb6.appspot.com",
  messagingSenderId: "83158396400",
  appId:             "1:83158396400:web:63f5f70d82130c47068135",
};
// ─────────────────────────────────────────────────────────────────────────────

const firebaseApp = initializeApp(firebaseConfig);
const auth        = getAuth(firebaseApp);
const provider    = new GoogleAuthProvider();

// Expose current user + ID token globally so other scripts can use them
window.currentUser    = null;
window.getIdToken     = async () => auth.currentUser ? auth.currentUser.getIdToken() : null;

// Called by "Sign in" button
window.signInWithGoogle = async () => {
  try {
    await signInWithPopup(auth, provider);
  } catch (e) {
    console.error('[Auth] sign-in error:', e.message);
  }
};

// Called by "Sign out" button
window.signOutUser = async () => {
  await signOut(auth);
};

// Update navbar whenever auth state changes
onAuthStateChanged(auth, async (user) => {
  window.currentUser = user;

  const btnSignIn  = document.getElementById('auth-signin-btn');
  const btnSignOut = document.getElementById('auth-signout-btn');
  const authName   = document.getElementById('auth-user-name');
  const authAvatar = document.getElementById('auth-user-avatar');

  if (user) {
    if (btnSignIn)  btnSignIn.style.display  = 'none';
    if (btnSignOut) btnSignOut.style.display = '';
    if (authName)   authName.textContent     = user.displayName || user.email;
    if (authName)   authName.style.display   = '';
    if (authAvatar && user.photoURL) {
      authAvatar.src           = user.photoURL;
      authAvatar.style.display = '';
    }
  } else {
    if (btnSignIn)  btnSignIn.style.display  = '';
    if (btnSignOut) btnSignOut.style.display = 'none';
    if (authName)   authName.style.display   = 'none';
    if (authAvatar) authAvatar.style.display = 'none';
  }
});
