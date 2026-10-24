import assert from 'node:assert/strict';
import { test } from 'node:test';
import { recognitionLocale, spokenLanguage } from '../src/voice/locale.ts';
import { validateTriage } from '../src/lib/contracts.ts';

test('auto mode preserves Hindi and Hinglish speech instead of forcing English', () => {
  assert.equal(recognitionLocale('auto'), 'hi-IN');
  assert.equal(recognitionLocale('en'), 'en-IN');
  assert.equal(spokenLanguage('auto', 'आपको किस तरह की देखभाल चाहिए?'), 'hi');
  assert.equal(spokenLanguage('auto', 'Papa ko bukhar hai'), 'hinglish');
  assert.equal(spokenLanguage('auto', 'What care do you need?'), 'en');
  assert.equal(spokenLanguage('hi', 'CBC report'), 'hi');
});
test('emergency normalization preserves Hindi response metadata', () => {
  const response = validateTriage({ care_type: 'emergency_112', response_language: 'hi', reasoning: 'तुरंत मदद लें।' });
  assert.equal(response.response_language, 'hi');
  assert.equal(response.matched_caregivers.length, 0);
});
