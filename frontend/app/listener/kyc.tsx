import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView, Alert,
  ActivityIndicator, Image, Animated, Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import api from '../../src/api';

type KYCStep = 'start' | 'upload_id' | 'confirm_data' | 'selfie' | 'processing' | 'result';
type KYCStatus = 'not_started' | 'in_progress' | 'pending_review' | 'verified' | 'rejected';

interface ExtractedData {
  name: string;
  dob: string;
  confidence: number;
}

interface AgeVerification {
  age: number;
  is_18_plus: boolean;
}

interface FinalResult {
  status: string;
  auto_approved: boolean;
  issues: string[];
  message: string;
}

export default function KYCScreen() {
  const router = useRouter();
  const [step, setStep] = useState<KYCStep>('start');
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  
  // Data states
  const [idType, setIdType] = useState<string>('aadhaar');
  const [idImage, setIdImage] = useState<string | null>(null);
  const [selfieImage, setSelfieImage] = useState<string | null>(null);
  const [extractedData, setExtractedData] = useState<ExtractedData | null>(null);
  const [ageVerification, setAgeVerification] = useState<AgeVerification | null>(null);
  const [finalResult, setFinalResult] = useState<FinalResult | null>(null);
  const [kycStatus, setKycStatus] = useState<KYCStatus>('not_started');
  
  // Animation
  const progressAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    loadKYCStatus();
  }, []);

  useEffect(() => {
    if (step === 'processing') {
      // Animate progress bar
      Animated.timing(progressAnim, {
        toValue: 1,
        duration: 3000,
        useNativeDriver: false,
      }).start();
      
      // Pulse animation
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.1, duration: 500, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 500, useNativeDriver: true }),
        ])
      ).start();
    }
  }, [step]);

  const loadKYCStatus = async () => {
    try {
      const res = await api.get('/kyc/status');
      setKycStatus(res.status);
      
      if (res.status === 'verified') {
        setStep('result');
        setFinalResult({ status: 'verified', auto_approved: true, issues: [], message: 'KYC verified' });
      } else if (res.status === 'pending_review') {
        setStep('result');
        setFinalResult({ status: 'pending_review', auto_approved: false, issues: res.final_result?.issues || [], message: res.message });
      } else if (res.status === 'rejected') {
        setStep('result');
        setFinalResult({ status: 'rejected', auto_approved: false, issues: res.final_result?.issues || [], message: res.message });
      } else if (res.step === 1 || res.step === 2) {
        setExtractedData(res.extracted_data ? { name: res.extracted_data.extracted_name, dob: res.extracted_data.extracted_dob, confidence: res.extracted_data.confidence } : null);
        setAgeVerification(res.age_verification);
        setStep(res.step === 2 ? 'selfie' : 'confirm_data');
      }
    } catch (e) {}
    setLoading(false);
  };

  const pickImage = async (forSelfie = false) => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission Required', 'Please allow access to your photos');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: forSelfie ? [1, 1] : [4, 3],
      quality: 0.7,
      base64: true,
    });

    if (!result.canceled && result.assets[0].base64) {
      if (forSelfie) {
        setSelfieImage(result.assets[0].base64);
      } else {
        setIdImage(result.assets[0].base64);
      }
    }
  };

  const takePhoto = async (forSelfie = false) => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission Required', 'Please allow camera access');
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      aspect: forSelfie ? [1, 1] : [4, 3],
      quality: 0.7,
      base64: true,
      cameraType: forSelfie ? ImagePicker.CameraType.front : ImagePicker.CameraType.back,
    });

    if (!result.canceled && result.assets[0].base64) {
      if (forSelfie) {
        setSelfieImage(result.assets[0].base64);
      } else {
        setIdImage(result.assets[0].base64);
      }
    }
  };

  const uploadID = async () => {
    if (!idImage) return Alert.alert('Error', 'Please select or capture your ID');
    
    setProcessing(true);
    try {
      const res = await api.post('/kyc/upload-id', {
        id_type: idType,
        id_image_base64: idImage,
      });
      
      if (res.success) {
        setExtractedData(res.extracted_data);
        setAgeVerification(res.age_verification);
        
        if (!res.age_verification?.is_18_plus) {
          Alert.alert('Age Verification Failed', 'You must be 18+ to use this platform');
          setStep('result');
          setFinalResult({ status: 'rejected', auto_approved: false, issues: ['underage'], message: 'Must be 18+' });
        } else {
          setStep('confirm_data');
        }
      }
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
    setProcessing(false);
  };

  const confirmData = async () => {
    setProcessing(true);
    try {
      const res = await api.post('/kyc/confirm-id-data');
      if (res.success) {
        setStep('selfie');
      }
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
    setProcessing(false);
  };

  const uploadSelfie = async () => {
    if (!selfieImage) return Alert.alert('Error', 'Please take a selfie');
    
    setStep('processing');
    setProcessing(true);
    
    try {
      const res = await api.post('/kyc/upload-selfie', {
        video_base64: selfieImage, // Using image for simplicity
      });
      
      // Wait for animation
      setTimeout(() => {
        setFinalResult(res.final_result);
        setStep('result');
        setProcessing(false);
      }, 3000);
    } catch (e: any) {
      Alert.alert('Error', e.message);
      setStep('selfie');
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#A2E3C4" />
        </View>
      </SafeAreaView>
    );
  }

  // RESULT SCREEN
  if (step === 'result') {
    const isVerified = finalResult?.status === 'verified';
    const isPending = finalResult?.status === 'pending_review';
    const isRejected = finalResult?.status === 'rejected';
    
    return (
      <SafeAreaView style={styles.container} testID="kyc-result-screen">
        <View style={styles.header}>
          <TouchableOpacity testID="kyc-back-btn" onPress={() => router.back()} style={styles.backBtn}>
            <Ionicons name="arrow-back" size={24} color="#2D3748" />
          </TouchableOpacity>
          <Text style={styles.title}>KYC Verification</Text>
        </View>
        
        <View style={styles.resultContainer}>
          <View style={[styles.resultIcon, { backgroundColor: isVerified ? '#E6FFED' : isPending ? '#FFF5E6' : '#FEE2E2' }]}>
            <Ionicons 
              name={isVerified ? 'shield-checkmark' : isPending ? 'hourglass' : 'close-circle'} 
              size={56} 
              color={isVerified ? '#48BB78' : isPending ? '#ED8936' : '#F56565'} 
            />
          </View>
          
          <Text style={styles.resultTitle}>
            {isVerified ? 'KYC Verified!' : isPending ? 'Under Review' : 'Verification Failed'}
          </Text>
          
          <Text style={styles.resultMessage}>
            {isVerified 
              ? 'Your identity has been verified. You can now receive calls and withdraw earnings.'
              : isPending
              ? 'Your documents are being reviewed by our team. This usually takes 24-48 hours.'
              : finalResult?.message || 'Please try again or contact support.'}
          </Text>
          
          {isPending && finalResult?.issues && finalResult.issues.length > 0 && (
            <View style={styles.issuesCard}>
              <Text style={styles.issuesTitle}>Review Notes:</Text>
              {finalResult.issues.map((issue, idx) => (
                <View key={idx} style={styles.issueRow}>
                  <Ionicons name="alert-circle" size={14} color="#ED8936" />
                  <Text style={styles.issueText}>{issue.replace(/_/g, ' ')}</Text>
                </View>
              ))}
            </View>
          )}
          
          {!isVerified && !isPending && (
            <TouchableOpacity 
              style={styles.retryBtn} 
              onPress={() => { setStep('start'); setIdImage(null); setSelfieImage(null); }}
            >
              <Text style={styles.retryBtnText}>Try Again</Text>
            </TouchableOpacity>
          )}
        </View>
      </SafeAreaView>
    );
  }

  // PROCESSING SCREEN
  if (step === 'processing') {
    return (
      <SafeAreaView style={styles.container} testID="kyc-processing-screen">
        <View style={styles.processingContainer}>
          <Animated.View style={[styles.processingIcon, { transform: [{ scale: pulseAnim }] }]}>
            <Ionicons name="scan" size={48} color="#A2E3C4" />
          </Animated.View>
          
          <Text style={styles.processingTitle}>Verifying Your Identity</Text>
          
          <View style={styles.progressBar}>
            <Animated.View style={[styles.progressFill, { 
              width: progressAnim.interpolate({ inputRange: [0, 1], outputRange: ['0%', '100%'] })
            }]} />
          </View>
          
          <View style={styles.checkList}>
            <CheckItem label="Extracting ID data" delay={0} />
            <CheckItem label="Verifying age (18+)" delay={800} />
            <CheckItem label="Detecting face" delay={1600} />
            <CheckItem label="Liveness check" delay={2000} />
            <CheckItem label="Matching faces" delay={2400} />
          </View>
        </View>
      </SafeAreaView>
    );
  }

  // START SCREEN
  if (step === 'start') {
    return (
      <SafeAreaView style={styles.container} testID="kyc-start-screen">
        <ScrollView contentContainerStyle={styles.scroll}>
          <View style={styles.header}>
            <TouchableOpacity testID="kyc-back-btn" onPress={() => router.back()} style={styles.backBtn}>
              <Ionicons name="arrow-back" size={24} color="#2D3748" />
            </TouchableOpacity>
            <Text style={styles.title}>KYC Verification</Text>
          </View>
          
          <View style={styles.heroCard}>
            <View style={styles.heroIcon}>
              <Ionicons name="shield-checkmark" size={40} color="#A2E3C4" />
            </View>
            <Text style={styles.heroTitle}>Verify Your Identity</Text>
            <Text style={styles.heroSub}>Quick 2-minute verification to start earning</Text>
          </View>
          
          <View style={styles.stepsCard}>
            <Text style={styles.stepsTitle}>How it works</Text>
            
            <View style={styles.stepRow}>
              <View style={[styles.stepIcon, { backgroundColor: '#E6FFED' }]}>
                <Ionicons name="card" size={20} color="#48BB78" />
              </View>
              <View style={styles.stepContent}>
                <Text style={styles.stepName}>1. Upload ID</Text>
                <Text style={styles.stepDesc}>Aadhaar, PAN, or Driving License</Text>
              </View>
            </View>
            
            <View style={styles.stepRow}>
              <View style={[styles.stepIcon, { backgroundColor: '#EBF5FB' }]}>
                <Ionicons name="eye" size={20} color="#85C1E9" />
              </View>
              <View style={styles.stepContent}>
                <Text style={styles.stepName}>2. Auto-Extract Data</Text>
                <Text style={styles.stepDesc}>We extract name & DOB automatically</Text>
              </View>
            </View>
            
            <View style={styles.stepRow}>
              <View style={[styles.stepIcon, { backgroundColor: '#FFF5E6' }]}>
                <Ionicons name="camera" size={20} color="#ED8936" />
              </View>
              <View style={styles.stepContent}>
                <Text style={styles.stepName}>3. Take Selfie</Text>
                <Text style={styles.stepDesc}>Liveness check & face matching</Text>
              </View>
            </View>
            
            <View style={styles.stepRow}>
              <View style={[styles.stepIcon, { backgroundColor: '#F0FFF4' }]}>
                <Ionicons name="checkmark-done" size={20} color="#38A169" />
              </View>
              <View style={styles.stepContent}>
                <Text style={styles.stepName}>4. Instant Verification</Text>
                <Text style={styles.stepDesc}>Auto-approved in most cases</Text>
              </View>
            </View>
          </View>
          
          <View style={styles.privacyCard}>
            <Ionicons name="lock-closed" size={16} color="#A2E3C4" />
            <Text style={styles.privacyText}>Your data is encrypted and stored securely. We only use it for verification.</Text>
          </View>
          
          <TouchableOpacity testID="kyc-start-btn" style={styles.primaryBtn} onPress={() => setStep('upload_id')}>
            <Text style={styles.primaryBtnText}>Start Verification</Text>
            <Ionicons name="arrow-forward" size={20} color="#1A4D2E" />
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // UPLOAD ID SCREEN
  if (step === 'upload_id') {
    return (
      <SafeAreaView style={styles.container} testID="kyc-upload-id-screen">
        <ScrollView contentContainerStyle={styles.scroll}>
          <View style={styles.header}>
            <TouchableOpacity onPress={() => setStep('start')} style={styles.backBtn}>
              <Ionicons name="arrow-back" size={24} color="#2D3748" />
            </TouchableOpacity>
            <Text style={styles.title}>Upload ID Document</Text>
          </View>
          
          <View style={styles.stepIndicator}>
            <View style={[styles.stepDot, styles.stepDotActive]} />
            <View style={styles.stepLine} />
            <View style={styles.stepDot} />
            <View style={styles.stepLine} />
            <View style={styles.stepDot} />
          </View>
          
          <Text style={styles.sectionTitle}>Select ID Type</Text>
          <View style={styles.idTypeRow}>
            {[
              { id: 'aadhaar', label: 'Aadhaar', icon: 'card' },
              { id: 'pan', label: 'PAN Card', icon: 'document' },
              { id: 'driving_license', label: 'License', icon: 'car' },
            ].map((type) => (
              <TouchableOpacity 
                key={type.id}
                style={[styles.idTypeCard, idType === type.id && styles.idTypeCardActive]}
                onPress={() => setIdType(type.id)}
              >
                <Ionicons name={type.icon as any} size={24} color={idType === type.id ? '#48BB78' : '#A0AEC0'} />
                <Text style={[styles.idTypeLabel, idType === type.id && styles.idTypeLabelActive]}>{type.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
          
          <Text style={styles.sectionTitle}>Upload Photo of ID</Text>
          
          {idImage ? (
            <View style={styles.imagePreview}>
              <Image source={{ uri: `data:image/jpeg;base64,${idImage}` }} style={styles.previewImage} />
              <TouchableOpacity style={styles.removeImageBtn} onPress={() => setIdImage(null)}>
                <Ionicons name="close-circle" size={28} color="#F56565" />
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.uploadOptions}>
              <TouchableOpacity style={styles.uploadBtn} onPress={() => takePhoto(false)}>
                <Ionicons name="camera" size={28} color="#48BB78" />
                <Text style={styles.uploadBtnText}>Take Photo</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.uploadBtn} onPress={() => pickImage(false)}>
                <Ionicons name="images" size={28} color="#85C1E9" />
                <Text style={styles.uploadBtnText}>Choose from Gallery</Text>
              </TouchableOpacity>
            </View>
          )}
          
          <View style={styles.tipsCard}>
            <Text style={styles.tipsTitle}>Tips for best results:</Text>
            <Text style={styles.tipItem}>• Ensure all text is clearly visible</Text>
            <Text style={styles.tipItem}>• Avoid glare and shadows</Text>
            <Text style={styles.tipItem}>• Place ID on a flat surface</Text>
          </View>
          
          <TouchableOpacity 
            style={[styles.primaryBtn, !idImage && styles.primaryBtnDisabled]} 
            onPress={uploadID}
            disabled={!idImage || processing}
          >
            {processing ? (
              <ActivityIndicator color="#1A4D2E" />
            ) : (
              <>
                <Text style={styles.primaryBtnText}>Extract Data</Text>
                <Ionicons name="scan" size={20} color="#1A4D2E" />
              </>
            )}
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // CONFIRM DATA SCREEN
  if (step === 'confirm_data') {
    return (
      <SafeAreaView style={styles.container} testID="kyc-confirm-screen">
        <ScrollView contentContainerStyle={styles.scroll}>
          <View style={styles.header}>
            <TouchableOpacity onPress={() => setStep('upload_id')} style={styles.backBtn}>
              <Ionicons name="arrow-back" size={24} color="#2D3748" />
            </TouchableOpacity>
            <Text style={styles.title}>Confirm Your Details</Text>
          </View>
          
          <View style={styles.stepIndicator}>
            <View style={[styles.stepDot, styles.stepDotCompleted]}><Ionicons name="checkmark" size={12} color="#fff" /></View>
            <View style={[styles.stepLine, styles.stepLineActive]} />
            <View style={[styles.stepDot, styles.stepDotActive]} />
            <View style={styles.stepLine} />
            <View style={styles.stepDot} />
          </View>
          
          <View style={styles.successBanner}>
            <Ionicons name="checkmark-circle" size={20} color="#48BB78" />
            <Text style={styles.successText}>Data extracted successfully!</Text>
          </View>
          
          <View style={styles.dataCard}>
            <View style={styles.dataRow}>
              <Text style={styles.dataLabel}>Full Name</Text>
              <Text style={styles.dataValue}>{extractedData?.name || 'N/A'}</Text>
            </View>
            <View style={styles.dataDivider} />
            <View style={styles.dataRow}>
              <Text style={styles.dataLabel}>Date of Birth</Text>
              <Text style={styles.dataValue}>{extractedData?.dob || 'N/A'}</Text>
            </View>
            <View style={styles.dataDivider} />
            <View style={styles.dataRow}>
              <Text style={styles.dataLabel}>Age</Text>
              <View style={styles.ageVerified}>
                <Text style={styles.dataValue}>{ageVerification?.age || 'N/A'} years</Text>
                {ageVerification?.is_18_plus && (
                  <View style={styles.verifiedBadge}>
                    <Ionicons name="checkmark" size={12} color="#fff" />
                    <Text style={styles.verifiedBadgeText}>18+</Text>
                  </View>
                )}
              </View>
            </View>
            <View style={styles.dataDivider} />
            <View style={styles.dataRow}>
              <Text style={styles.dataLabel}>Confidence</Text>
              <View style={styles.confidenceBar}>
                <View style={[styles.confidenceFill, { width: `${(extractedData?.confidence || 0) * 100}%` }]} />
              </View>
              <Text style={styles.confidenceText}>{Math.round((extractedData?.confidence || 0) * 100)}%</Text>
            </View>
          </View>
          
          <View style={styles.infoCard}>
            <Ionicons name="information-circle" size={18} color="#85C1E9" />
            <Text style={styles.infoText}>Please verify the extracted information is correct before proceeding.</Text>
          </View>
          
          <TouchableOpacity style={styles.primaryBtn} onPress={confirmData} disabled={processing}>
            {processing ? (
              <ActivityIndicator color="#1A4D2E" />
            ) : (
              <>
                <Text style={styles.primaryBtnText}>Confirm & Continue</Text>
                <Ionicons name="arrow-forward" size={20} color="#1A4D2E" />
              </>
            )}
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.secondaryBtn} onPress={() => { setStep('upload_id'); setIdImage(null); }}>
            <Text style={styles.secondaryBtnText}>Re-upload ID</Text>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // SELFIE SCREEN
  if (step === 'selfie') {
    return (
      <SafeAreaView style={styles.container} testID="kyc-selfie-screen">
        <ScrollView contentContainerStyle={styles.scroll}>
          <View style={styles.header}>
            <TouchableOpacity onPress={() => setStep('confirm_data')} style={styles.backBtn}>
              <Ionicons name="arrow-back" size={24} color="#2D3748" />
            </TouchableOpacity>
            <Text style={styles.title}>Take a Selfie</Text>
          </View>
          
          <View style={styles.stepIndicator}>
            <View style={[styles.stepDot, styles.stepDotCompleted]}><Ionicons name="checkmark" size={12} color="#fff" /></View>
            <View style={[styles.stepLine, styles.stepLineActive]} />
            <View style={[styles.stepDot, styles.stepDotCompleted]}><Ionicons name="checkmark" size={12} color="#fff" /></View>
            <View style={[styles.stepLine, styles.stepLineActive]} />
            <View style={[styles.stepDot, styles.stepDotActive]} />
          </View>
          
          <View style={styles.selfieInstructions}>
            <Ionicons name="happy" size={48} color="#A2E3C4" />
            <Text style={styles.selfieTitle}>Face Verification</Text>
            <Text style={styles.selfieSub}>Take a clear selfie for liveness check</Text>
          </View>
          
          {selfieImage ? (
            <View style={styles.selfiePreview}>
              <Image source={{ uri: `data:image/jpeg;base64,${selfieImage}` }} style={styles.selfieImage} />
              <TouchableOpacity style={styles.removeImageBtn} onPress={() => setSelfieImage(null)}>
                <Ionicons name="close-circle" size={28} color="#F56565" />
              </TouchableOpacity>
            </View>
          ) : (
            <TouchableOpacity style={styles.selfieCapture} onPress={() => takePhoto(true)}>
              <View style={styles.selfieCircle}>
                <Ionicons name="camera" size={40} color="#A2E3C4" />
              </View>
              <Text style={styles.selfieCaptureText}>Tap to take selfie</Text>
            </TouchableOpacity>
          )}
          
          <View style={styles.selfieTips}>
            <View style={styles.selfieTip}>
              <Ionicons name="sunny" size={18} color="#F6E05E" />
              <Text style={styles.selfieTipText}>Good lighting</Text>
            </View>
            <View style={styles.selfieTip}>
              <Ionicons name="eye" size={18} color="#85C1E9" />
              <Text style={styles.selfieTipText}>Face the camera</Text>
            </View>
            <View style={styles.selfieTip}>
              <Ionicons name="glasses" size={18} color="#BB8FCE" />
              <Text style={styles.selfieTipText}>Remove glasses</Text>
            </View>
          </View>
          
          <TouchableOpacity 
            style={[styles.primaryBtn, !selfieImage && styles.primaryBtnDisabled]} 
            onPress={uploadSelfie}
            disabled={!selfieImage || processing}
          >
            <Text style={styles.primaryBtnText}>Verify Identity</Text>
            <Ionicons name="shield-checkmark" size={20} color="#1A4D2E" />
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return null;
}

// Animated check item for processing screen
function CheckItem({ label, delay }: { label: string; delay: number }) {
  const [checked, setChecked] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setChecked(true);
      Animated.timing(fadeAnim, { toValue: 1, duration: 300, useNativeDriver: true }).start();
    }, delay);
    return () => clearTimeout(timer);
  }, [delay]);
  
  return (
    <View style={styles.checkItem}>
      <Animated.View style={{ opacity: fadeAnim }}>
        <Ionicons name={checked ? 'checkmark-circle' : 'ellipse-outline'} size={20} color={checked ? '#48BB78' : '#E2E8F0'} />
      </Animated.View>
      <Text style={[styles.checkLabel, checked && styles.checkLabelDone]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFBF0' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  scroll: { paddingBottom: 40 },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingTop: 8, paddingBottom: 16, gap: 12 },
  backBtn: { width: 40, height: 40, borderRadius: 12, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 20, fontWeight: '700', color: '#2D3748' },
  
  // Step indicator
  stepIndicator: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 16, gap: 4 },
  stepDot: { width: 24, height: 24, borderRadius: 12, backgroundColor: '#E2E8F0', alignItems: 'center', justifyContent: 'center' },
  stepDotActive: { backgroundColor: '#A2E3C4' },
  stepDotCompleted: { backgroundColor: '#48BB78' },
  stepLine: { width: 40, height: 3, backgroundColor: '#E2E8F0', borderRadius: 2 },
  stepLineActive: { backgroundColor: '#48BB78' },
  
  // Hero card
  heroCard: { alignItems: 'center', paddingVertical: 32, marginHorizontal: 20, backgroundColor: '#fff', borderRadius: 20, marginBottom: 20 },
  heroIcon: { width: 80, height: 80, borderRadius: 40, backgroundColor: '#E6FFED', alignItems: 'center', justifyContent: 'center', marginBottom: 16 },
  heroTitle: { fontSize: 22, fontWeight: '700', color: '#2D3748' },
  heroSub: { fontSize: 14, color: '#718096', marginTop: 4 },
  
  // Steps card
  stepsCard: { backgroundColor: '#fff', borderRadius: 18, padding: 20, marginHorizontal: 20, marginBottom: 16 },
  stepsTitle: { fontSize: 16, fontWeight: '700', color: '#2D3748', marginBottom: 16 },
  stepRow: { flexDirection: 'row', alignItems: 'center', gap: 14, marginBottom: 16 },
  stepIcon: { width: 44, height: 44, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  stepContent: { flex: 1 },
  stepName: { fontSize: 14, fontWeight: '600', color: '#2D3748' },
  stepDesc: { fontSize: 12, color: '#718096', marginTop: 2 },
  
  // Privacy card
  privacyCard: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#E6FFED', borderRadius: 12, padding: 12, marginHorizontal: 20, marginBottom: 20 },
  privacyText: { fontSize: 11, color: '#1A4D2E', flex: 1 },
  
  // Buttons
  primaryBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: '#A2E3C4', paddingVertical: 16, borderRadius: 28, marginHorizontal: 20 },
  primaryBtnDisabled: { opacity: 0.5 },
  primaryBtnText: { fontSize: 16, fontWeight: '700', color: '#1A4D2E' },
  secondaryBtn: { alignItems: 'center', paddingVertical: 12, marginTop: 12 },
  secondaryBtnText: { fontSize: 14, fontWeight: '600', color: '#718096' },
  
  // ID Type selection
  sectionTitle: { fontSize: 14, fontWeight: '600', color: '#4A5568', marginHorizontal: 20, marginBottom: 12, marginTop: 8 },
  idTypeRow: { flexDirection: 'row', gap: 10, paddingHorizontal: 20, marginBottom: 20 },
  idTypeCard: { flex: 1, alignItems: 'center', paddingVertical: 16, backgroundColor: '#fff', borderRadius: 14, borderWidth: 2, borderColor: '#E2E8F0' },
  idTypeCardActive: { borderColor: '#48BB78', backgroundColor: '#F0FFF4' },
  idTypeLabel: { fontSize: 12, fontWeight: '600', color: '#718096', marginTop: 6 },
  idTypeLabelActive: { color: '#48BB78' },
  
  // Upload options
  uploadOptions: { flexDirection: 'row', gap: 12, paddingHorizontal: 20, marginBottom: 20 },
  uploadBtn: { flex: 1, alignItems: 'center', paddingVertical: 24, backgroundColor: '#fff', borderRadius: 16, borderWidth: 2, borderColor: '#E2E8F0', borderStyle: 'dashed' },
  uploadBtnText: { fontSize: 13, fontWeight: '600', color: '#4A5568', marginTop: 8 },
  
  // Image preview
  imagePreview: { marginHorizontal: 20, marginBottom: 20, position: 'relative' },
  previewImage: { width: '100%', height: 200, borderRadius: 16 },
  removeImageBtn: { position: 'absolute', top: -10, right: -10 },
  
  // Tips
  tipsCard: { backgroundColor: '#FFF5E6', borderRadius: 14, padding: 14, marginHorizontal: 20, marginBottom: 20 },
  tipsTitle: { fontSize: 13, fontWeight: '700', color: '#744210', marginBottom: 8 },
  tipItem: { fontSize: 12, color: '#744210', marginBottom: 4 },
  
  // Data confirmation
  successBanner: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#E6FFED', borderRadius: 12, padding: 12, marginHorizontal: 20, marginBottom: 16 },
  successText: { fontSize: 13, fontWeight: '600', color: '#48BB78' },
  dataCard: { backgroundColor: '#fff', borderRadius: 18, padding: 20, marginHorizontal: 20, marginBottom: 16 },
  dataRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 12 },
  dataLabel: { fontSize: 13, color: '#718096', fontWeight: '500' },
  dataValue: { fontSize: 15, fontWeight: '600', color: '#2D3748' },
  dataDivider: { height: 1, backgroundColor: '#F0F0F0' },
  ageVerified: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  verifiedBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#48BB78', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 10 },
  verifiedBadgeText: { fontSize: 11, fontWeight: '700', color: '#fff' },
  confidenceBar: { width: 80, height: 6, backgroundColor: '#E2E8F0', borderRadius: 3, overflow: 'hidden' },
  confidenceFill: { height: '100%', backgroundColor: '#48BB78', borderRadius: 3 },
  confidenceText: { fontSize: 12, fontWeight: '600', color: '#48BB78', marginLeft: 8 },
  infoCard: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#EBF5FB', borderRadius: 12, padding: 12, marginHorizontal: 20, marginBottom: 20 },
  infoText: { fontSize: 12, color: '#2E86AB', flex: 1 },
  
  // Selfie
  selfieInstructions: { alignItems: 'center', paddingVertical: 20, marginHorizontal: 20 },
  selfieTitle: { fontSize: 20, fontWeight: '700', color: '#2D3748', marginTop: 12 },
  selfieSub: { fontSize: 14, color: '#718096', marginTop: 4 },
  selfieCapture: { alignItems: 'center', marginHorizontal: 20, marginVertical: 20 },
  selfieCircle: { width: 160, height: 160, borderRadius: 80, backgroundColor: '#fff', borderWidth: 4, borderColor: '#A2E3C4', borderStyle: 'dashed', alignItems: 'center', justifyContent: 'center' },
  selfieCaptureText: { fontSize: 14, fontWeight: '600', color: '#718096', marginTop: 12 },
  selfiePreview: { alignItems: 'center', marginHorizontal: 20, marginVertical: 20, position: 'relative' },
  selfieImage: { width: 180, height: 180, borderRadius: 90, borderWidth: 4, borderColor: '#A2E3C4' },
  selfieTips: { flexDirection: 'row', justifyContent: 'center', gap: 16, marginBottom: 24 },
  selfieTip: { alignItems: 'center', gap: 4 },
  selfieTipText: { fontSize: 11, color: '#718096', fontWeight: '500' },
  
  // Processing
  processingContainer: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 40 },
  processingIcon: { width: 100, height: 100, borderRadius: 50, backgroundColor: '#E6FFED', alignItems: 'center', justifyContent: 'center', marginBottom: 24 },
  processingTitle: { fontSize: 20, fontWeight: '700', color: '#2D3748', marginBottom: 24 },
  progressBar: { width: '100%', height: 8, backgroundColor: '#E2E8F0', borderRadius: 4, overflow: 'hidden', marginBottom: 32 },
  progressFill: { height: '100%', backgroundColor: '#A2E3C4', borderRadius: 4 },
  checkList: { width: '100%' },
  checkItem: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 12 },
  checkLabel: { fontSize: 14, color: '#A0AEC0', fontWeight: '500' },
  checkLabelDone: { color: '#2D3748' },
  
  // Result
  resultContainer: { flex: 1, alignItems: 'center', paddingTop: 60, paddingHorizontal: 20 },
  resultIcon: { width: 120, height: 120, borderRadius: 60, alignItems: 'center', justifyContent: 'center', marginBottom: 24 },
  resultTitle: { fontSize: 24, fontWeight: '700', color: '#2D3748', marginBottom: 12 },
  resultMessage: { fontSize: 14, color: '#718096', textAlign: 'center', lineHeight: 22, marginBottom: 24 },
  issuesCard: { backgroundColor: '#FFF5E6', borderRadius: 14, padding: 16, width: '100%', marginBottom: 24 },
  issuesTitle: { fontSize: 13, fontWeight: '700', color: '#744210', marginBottom: 8 },
  issueRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6 },
  issueText: { fontSize: 12, color: '#744210', textTransform: 'capitalize' },
  retryBtn: { backgroundColor: '#F56565', paddingHorizontal: 32, paddingVertical: 14, borderRadius: 24 },
  retryBtnText: { fontSize: 15, fontWeight: '700', color: '#fff' },
});
