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
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
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

// Email/password auth (SCOPE Phase 2). Resolve to the user on success or throw.
window.signInWithEmail = async (email, password) => {
  const cred = await signInWithEmailAndPassword(auth, email, password);
  return cred.user;
};

window.signUpWithEmail = async (email, password) => {
  const cred = await createUserWithEmailAndPassword(auth, email, password);
  return cred.user;
};

// Called by "Sign out" button
window.signOutUser = async () => {
  await signOut(auth);
};

// ── Authenticated fetch + submission gating ──────────────────────────────────
// Wraps fetch and attaches the current user's Firebase ID token as a Bearer
// header. The server verifies this token on gated routes (submissions), so the
// token — not a spoofable client flag — is what authorizes the write.
window.authedFetch = async (url, options = {}) => {
  const token = await window.getIdToken();
  const headers = { ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return fetch(url, { ...options, headers });
};

// Opens the sign-in modal if present; otherwise falls back to a Google popup.
window.openAuthModal = () => {
  const el = document.getElementById('authModal');
  if (el && window.bootstrap && window.bootstrap.Modal) {
    window.bootstrap.Modal.getOrCreateInstance(el).show();
  } else {
    window.signInWithGoogle();
  }
};

// Returns true if a user is signed in; otherwise prompts sign-in and returns false.
// Submission forms call this before sending so anonymous users get a clear
// "sign in to contribute" path instead of a silent 401.
window.requireSignIn = (message) => {
  if (window.currentUser) return true;
  if (typeof window.siteToast === 'function') {
    window.siteToast(message || 'Please sign in to contribute.', 'error');
  }
  window.openAuthModal();
  return false;
};

// ── Sign-in modal wiring (email/password + Google) ───────────────────────────
let _authMode = 'signin'; // 'signin' | 'signup'
function _setAuthError(msg) {
  const e = document.getElementById('auth-error');
  if (e) e.textContent = msg || '';
}
function _friendlyAuthError(code) {
  switch (code) {
    case 'auth/invalid-email':        return 'That email address looks invalid.';
    case 'auth/missing-password':     return 'Please enter a password.';
    case 'auth/weak-password':        return 'Password should be at least 6 characters.';
    case 'auth/email-already-in-use': return 'An account already exists for that email — try signing in.';
    case 'auth/invalid-credential':
    case 'auth/wrong-password':
    case 'auth/user-not-found':       return 'Email or password is incorrect.';
    default:                          return 'Something went wrong. Please try again.';
  }
}
function initAuthModal() {
  const form = document.getElementById('auth-email-form');
  if (!form) return;
  const toggle    = document.getElementById('auth-toggle-mode');
  const submitBtn = document.getElementById('auth-submit-btn');
  const title     = document.getElementById('auth-modal-title');
  const googleBtn = document.getElementById('auth-google-modal-btn');

  function applyMode() {
    const signup = _authMode === 'signup';
    if (title)     title.textContent     = signup ? 'Create your account' : 'Sign in';
    if (submitBtn) submitBtn.textContent = signup ? 'Create account' : 'Sign in';
    if (toggle)    toggle.innerHTML = signup
      ? 'Already have an account? <a href="#" role="button">Sign in</a>'
      : 'New here? <a href="#" role="button">Create an account</a>';
    _setAuthError('');
  }
  applyMode();

  if (toggle) toggle.addEventListener('click', (e) => {
    if (e.target.tagName === 'A') { e.preventDefault(); _authMode = _authMode === 'signup' ? 'signin' : 'signup'; applyMode(); }
  });
  if (googleBtn) googleBtn.addEventListener('click', () => window.signInWithGoogle());

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    _setAuthError('');
    const email = document.getElementById('auth-email').value.trim();
    const pw    = document.getElementById('auth-password').value;
    if (submitBtn) { submitBtn.disabled = true; submitBtn.dataset._t = submitBtn.textContent; submitBtn.textContent = 'Please wait…'; }
    try {
      if (_authMode === 'signup') await window.signUpWithEmail(email, pw);
      else                        await window.signInWithEmail(email, pw);
      form.reset();
      // onAuthStateChanged closes the modal on success.
    } catch (err) {
      _setAuthError(_friendlyAuthError(err && err.code));
    } finally {
      if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = submitBtn.dataset._t || 'Sign in'; }
    }
  });
}
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAuthModal);
} else {
  initAuthModal();
}

// Update navbar whenever auth state changes, broadcast for other pages, and
// close the sign-in modal once a user is signed in.
onAuthStateChanged(auth, async (user) => {
  window.currentUser = user;

  const btnSignIn  = document.getElementById('auth-signin-btn');
  const btnSignOut = document.getElementById('auth-signout-btn');
  const authName   = document.getElementById('auth-user-name');
  const authAvatar = document.getElementById('auth-user-avatar');
  const profileLi  = document.getElementById('auth-profile-li');

  if (user) {
    if (btnSignIn)  btnSignIn.style.display  = 'none';
    if (btnSignOut) btnSignOut.style.display = '';
    if (authName)   authName.textContent     = user.displayName || user.email;
    if (authName)   authName.style.display   = '';
    if (profileLi)  profileLi.style.display   = '';
    if (authAvatar && user.photoURL) {
      authAvatar.src           = user.photoURL;
      authAvatar.style.display = '';
    }
    // Close the auth modal if it's open.
    const modalEl = document.getElementById('authModal');
    if (modalEl && window.bootstrap && window.bootstrap.Modal) {
      const inst = window.bootstrap.Modal.getInstance(modalEl);
      if (inst) inst.hide();
    }
  } else {
    if (btnSignIn)  btnSignIn.style.display  = '';
    if (btnSignOut) btnSignOut.style.display = 'none';
    if (authName)   authName.style.display   = 'none';
    if (profileLi)  profileLi.style.display   = 'none';
    if (authAvatar) authAvatar.style.display = 'none';
  }

  // Broadcast so non-index pages (e.g. profile.html) can react.
  document.dispatchEvent(new CustomEvent('auth-changed', { detail: { user } }));
});
