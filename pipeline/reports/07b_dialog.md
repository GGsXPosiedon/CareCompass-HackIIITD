# Stage 7b: follow-up dialog policy (rule baseline)

Replayed conversations, `c01` is the failing live-demo chat. Author-written and unreviewed; this shows the logic works, not that the wording is clinically right.

| case | user message | action | slot | assistant reply |
|---|---|---|---|---|
| c01 | 2+2=? | redirect |  | I can help with health and home-care needs. Could you tell me in a few words what is wrong, or who is unwell? |
| c01 | abba dabba jabba | redirect |  | I can help with health and home-care needs. Could you tell me in a few words what is wrong, or who is unwell? |
| c01 | i want to watch netflix | redirect |  | I can help with health and home-care needs. Could you tell me in a few words what is wrong, or who is unwell? |
| c01 | mujhe bukhar hai | ask | duration | bukhar kab se hai? |
| c01 | 2 din se | ask | temperature | Kya aapne temperature naapa? Agar haan, to kitna hai? |
| c01 | 101 | commit |  |  |
| c02 | mujhe bukhar hai | ask | duration | bukhar kab se hai? |
| c02 | mujhe medic nhi chaiyeee mujhe koi bhi nhi chaiye mai ekele hi theek hu | acknowledge_decline |  | Samajh gaya, main kuch book nahi karunga. Mann badle to main yahan hoon. Agar saans lene mein taklif, seene mein dard ya confusion ho to kripya 112 par call karein. |
| c02 | bhaad me jaaaa | deescalate |  | Agar maine aapko pareshan kiya to maaf kijiye. Main yahin rukta hoon, jab bhi madad chahiye mujhe likh dijiyega. |
| c03 | 3 din se bukhar hai, 102 degree | ask | associated | Kya iske saath kuch aur bhi hai, jaise khansi, saans mein taklif, ulti ya daane? |
| c03 | nahi | ask | patient | Yeh kiske liye hai, aur unki umar kya hai? |
| c03 | mere papa ke liye, 60 saal | commit |  |  |
| c04 | I have knee pain | ask | severity_pain | How bad is the knee pain on a scale of 1 to 10, and does it stop you from moving or walking? |
| c04 | about 6, it hurts to walk | ask | duration | How long have you had the knee pain? |
| c04 | since last week | commit |  |  |
| c05 | my son has fever | ask | duration | How long have you had the fever? |
| c05 | since yesterday | ask | temperature | Have you checked the temperature? If yes, what does it show? |
| c05 | not checked | commit |  |  |
| c06 | mujhe jeena nahi hai | crisis_safety |  | Mujhe bahut dukh hai ki aap aisa mehsoos kar rahe hain, aap akele nahi hain. Agar aap khud ko nuksaan pahuncha sakte hain to abhi 112 par call karein ya paas kisi ko batayein. Main yahan hoon aur support dhoondhne mein madad kar sakta hoon. |
| c07 | I want to die | crisis_safety |  | I'm really sorry you are feeling this way, and you don't have to face it alone. If you might hurt yourself, please call 112 now or tell someone near you. I can stay here and help you find support. |
| c08 | chest pain ho raha hai | defer_to_safety |  |  |
| c09 | bukhar hai | ask | duration | bukhar kab se hai? |
| c09 | pata nahi | ask | temperature | Kya aapne temperature naapa? Agar haan, to kitna hai? |
| c09 | pata nahi | commit |  |  |
| c10 | I don't need any help | acknowledge_decline |  | Understood, I won't book anything. If you change your mind I'm here. If there is trouble breathing, chest pain or confusion, please call 112. |
| c11 | hello | greet |  | Hello! Tell me what is troubling you or someone in your family, and I will help find the right care. |
| c12 | asdf | redirect |  | I can help with health and home-care needs. Could you tell me in a few words what is wrong, or who is unwell? |
| c12 | qwerty | redirect |  | I can help with health and home-care needs. Could you tell me in a few words what is wrong, or who is unwell? |
| c12 | lol | redirect |  | I can help with health and home-care needs. Could you tell me in a few words what is wrong, or who is unwell? |
| c12 | hmm hmm | offer_exit |  | I can help whenever you need health or home care. Just tell me what is wrong. |
| c13 | मुझे बुखार है | ask | duration | बुखार कब से है? |
| c13 | 2 दिन से | ask | temperature | क्या आपने तापमान नापा? अगर हाँ, तो कितना है? |
| c14 | mujhe bahut ghabrahat ho rahi hai | redirect |  | Yeh stressful lag raha hai, main madad ke liye yahan hoon. Kya aap bata sakte hain ki kya ho raha hai? |
| c15 | bukhar hai but doctor nahi chahiye | acknowledge_decline |  | Samajh gaya, main kuch book nahi karunga. Mann badle to main yahan hoon. Agar saans lene mein taklif, seene mein dard ya confusion ho to kripya 112 par call karein. |
| c16 | sir dard hai | ask | severity_pain | sir dard 1 se 10 mein kitna tez hai, aur kya isse chalne-phirne mein dikkat ho rahi hai? |
| c16 | 7 hai | ask | duration | sir dard kab se hai? |
| c17 | knee pain since 2 days, 5 out of 10 | ask | associated | Is there anything else along with it, such as swelling, redness, fever or trouble walking? |
