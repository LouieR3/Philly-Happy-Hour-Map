// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyAK2bb2zN7ibRWsgc7SSU5ibUOHwpbksEI",
  authDomain: "mappy-hour-39fb6.firebaseapp.com",
  projectId: "mappy-hour-39fb6",
  storageBucket: "mappy-hour-39fb6.appspot.com",
  messagingSenderId: "83158396400",
  appId: "1:83158396400:web:63f5f70d82130c47068135",
  measurementId: "G-N53HSGZY66"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);

//middleware
app.use(cors());
app.use(express.json()); //req.body