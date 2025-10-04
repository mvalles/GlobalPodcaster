// firebaseConfig.ts
// Reemplaza los valores con los de tu proyecto Firebase

import { initializeApp, getApps, getApp, type FirebaseApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getStorage } from "firebase/storage";

const firebaseConfig = {
  apiKey: "AIzaSyAMg9u2g7pfM7ndRSdQk3QOITy5clgW2ts",
  authDomain: "global-podcaster.firebaseapp.com",
  projectId: "global-podcaster",
  // Use the canonical appspot.com bucket domain for Firebase Storage
  storageBucket: "global-podcaster.appspot.com",
  messagingSenderId: "837642332791",
  appId: "1:837642332791:web:305d071d8ba94accb1f472"
};

// Avoid duplicate initialization in SSR/dev HMR by reusing the default app if it exists
const app: FirebaseApp = getApps().length ? getApp() : initializeApp(firebaseConfig);

export const auth = getAuth(app);
export const storage = getStorage(app);
