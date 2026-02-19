import auth from '@react-native-firebase/auth';

/**
 * Firebase Phone Authentication helpers.
 *
 * Firebase is initialised automatically by @react-native-firebase/app
 * using google-services.json (Android) and GoogleService-Info.plist (iOS)
 * bundled at build time via the Expo config plugin.
 */

/** Send OTP to the given phone number (E.164 format, e.g. "+919876543210"). */
export async function sendFirebaseOtp(phoneNumber: string) {
  const confirmation = await auth().signInWithPhoneNumber(phoneNumber);
  return confirmation;
}

/** Get the current Firebase user's ID token to send to the backend. */
export async function getFirebaseIdToken(): Promise<string | null> {
  const user = auth().currentUser;
  if (!user) return null;
  return user.getIdToken(/* forceRefresh */ true);
}

/** Sign out from Firebase. */
export async function firebaseSignOut() {
  await auth().signOut();
}

export default auth;
