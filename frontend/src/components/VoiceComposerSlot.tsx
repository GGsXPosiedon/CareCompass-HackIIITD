import { useContext } from 'react';
import { VoiceComposerHostContext } from '../voice/language';
// The session owner stays mounted in App; only its controls move between chat composers.
export function VoiceComposerSlot() {
  const bind = useContext(VoiceComposerHostContext);
  return <div ref={bind} className="voice-composer-slot"/>;
}
