import type { Caregiver, Location } from './types';

// Entirely synthetic demo profiles. Not actual providers, availability, ratings, or distances.
export const caregivers: Caregiver[] = [
  { id: 'CG_014', name: 'Aarav Mehta', initials: 'AM', role: 'Paramedic', roleHi: 'पैरामेडिक', careType: 'paramedic_home_visit', experience: 6, distance: 2.4, languages: ['Hindi', 'English'], rating: 4.9, reviews: 128, skills: ['Home assessments', 'Vitals monitoring'], skillsHi: ['घर पर मूल्यांकन', 'वाइटल्स की जाँच'], slots: ['10:00', '14:00', '16:30'], tint: 'sage' },
  { id: 'CG_022', name: 'Simran Kaur', initials: 'SK', role: 'Paramedic', roleHi: 'पैरामेडिक', careType: 'paramedic_home_visit', experience: 8, distance: 3.1, languages: ['Hindi', 'English', 'Punjabi'], rating: 4.8, reviews: 96, skills: ['Home assessments', 'Elderly care'], skillsHi: ['घर पर मूल्यांकन', 'बुज़ुर्गों की देखभाल'], slots: ['11:30', '15:00', '17:00'], tint: 'rose' },
  { id: 'CG_031', name: 'Rohan Das', initials: 'RD', role: 'Paramedic', roleHi: 'पैरामेडिक', careType: 'paramedic_home_visit', experience: 4, distance: 4.6, languages: ['Hindi', 'English', 'Bengali'], rating: 4.8, reviews: 74, skills: ['Vitals monitoring', 'Home assessments'], skillsHi: ['वाइटल्स की जाँच', 'घर पर मूल्यांकन'], slots: ['12:00', '16:00'], tint: 'blue' },
  { id: 'CG_008', name: 'Neha Sharma', initials: 'NS', role: 'Registered nurse', roleHi: 'पंजीकृत नर्स', careType: 'home_nursing', experience: 7, distance: 1.8, languages: ['Hindi', 'English'], rating: 4.9, reviews: 112, skills: ['Wound dressing', 'Post-operative care'], skillsHi: ['घाव की ड्रेसिंग', 'ऑपरेशन के बाद देखभाल'], slots: ['09:30', '13:00', '17:30'], tint: 'sage' },
  { id: 'CG_019', name: 'Priya Nair', initials: 'PN', role: 'Registered nurse', roleHi: 'पंजीकृत नर्स', careType: 'home_nursing', experience: 5, distance: 3.2, languages: ['Hindi', 'English', 'Malayalam'], rating: 4.8, reviews: 89, skills: ['Wound dressing', 'Elderly care'], skillsHi: ['घाव की ड्रेसिंग', 'बुज़ुर्गों की देखभाल'], slots: ['10:30', '14:30'], tint: 'blue' },
  { id: 'CG_042', name: 'Dr. Ananya Rao', initials: 'AR', role: 'General physician', roleHi: 'सामान्य चिकित्सक', careType: 'teleconsultation', experience: 9, distance: 0, languages: ['Hindi', 'English'], rating: 4.9, reviews: 154, skills: ['General consultation', 'Follow-up care'], skillsHi: ['सामान्य परामर्श', 'फ़ॉलो-अप देखभाल'], slots: ['10:15', '12:30', '16:15'], tint: 'rose' },
  { id: 'CG_050', name: 'Karan Mehta', initials: 'KM', role: 'Lab technician', roleHi: 'लैब तकनीशियन', careType: 'lab_test_home', experience: 7, distance: 3.9, languages: ['Hindi', 'English'], rating: 4.7, reviews: 83, skills: ['Home sample collection'], skillsHi: ['घर पर सैंपल कलेक्शन'], slots: ['08:00', '10:00', '12:00'], tint: 'sand' },
];
export const locations: Location[] = [
  { label: 'Okhla, New Delhi', lat: 28.54, lng: 77.27 },
  { label: 'Greater Kailash, New Delhi', lat: 28.549, lng: 77.235 },
  { label: 'Saket, New Delhi', lat: 28.524, lng: 77.206 },
  { label: 'Outside demo coverage', lat: 0, lng: 0 },
];
export const scenarios = [
  { id: 'fever', en: 'Fever & cough', hi: 'बुखार और खाँसी', text: 'My father has had fever and cough for two days.', textHi: 'पापा को दो दिन से बुखार और खाँसी है।', hinglish: 'Papa ko do din se bukhar hai aur khansi bhi.' },
  { id: 'dressing', en: 'Dressing change', hi: 'ड्रेसिंग बदलना', text: 'I need a routine wound dressing change after surgery.', textHi: 'ऑपरेशन के बाद घाव की नियमित ड्रेसिंग बदलवानी है।', hinglish: 'Operation ke baad wound ki routine dressing change karwani hai.' },
  { id: 'consult', en: 'Doctor consultation', hi: 'डॉक्टर से परामर्श', text: 'I need a routine doctor consultation for a follow-up.', textHi: 'मुझे फ़ॉलो-अप के लिए डॉक्टर से नियमित परामर्श चाहिए।', hinglish: 'Mujhe follow-up ke liye routine doctor consultation chahiye.' },
];
export const emergencyExample = { en: 'This is an emergency demo. My father cannot breathe.', hi: 'यह आपातकाल का डेमो है। पापा को साँस नहीं आ रही है।' };
