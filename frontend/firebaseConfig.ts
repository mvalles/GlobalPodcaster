// firebaseConfig.ts
// Reemplaza los valores con los de tu proyecto Firebase

import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyAMg9u2g7pfM7ndRSdQk3QOITy5clgW2ts",
  authDomain: "global-podcaster.firebaseapp.com",
  projectId: "global-podcaster",
  storageBucket: "global-podcaster.firebasestorage.app",
  messagingSenderId: "837642332791",
  appId: "1:837642332791:web:305d071d8ba94accb1f472"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
