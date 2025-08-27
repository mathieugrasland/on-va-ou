// Configuration Firebase côté client
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: "AIzaSyBs1O6cYYxNLE2vB9gEcmhEhONrditDyCo",
  authDomain: "on-va-ou-470217.firebaseapp.com",
  projectId: "on-va-ou-470217",
  storageBucket: "on-va-ou-470217.firebasestorage.app",
  messagingSenderId: "687464295451",
  appId: "1:687464295451:web:b228ea2a0ddc668e5f1cbe",
  measurementId: "G-2PCHXTT6DW"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
