# Quick Fix for Alexa Skill Slot Types

## The Problem

You're getting errors about "phrase slots" because `AMAZON.SearchQuery` and `AMAZON.MedicationName` don't work well with other slots in the same utterance.

## The Solution

Use **custom slot types** for both `prescriptionName` and `hasRefills`.

---

## Step-by-Step Fix

### 1. Create PrescriptionNameType

1. Go to **Slot Types** in left sidebar
2. Click **"+ Add Slot Type"**
3. Select **"Create custom slot type"**
4. Name: `PrescriptionNameType`
5. Add these values (one per line):
   ```
   Aspirin
   Ibuprofen
   Acetaminophen
   Tylenol
   Advil
   Vitamin D
   Vitamin C
   Calcium
   Multivitamin
   Fish Oil
   Lisinopril
   Metformin
   Atorvastatin
   Omeprazole
   Levothyroxine
   ```
6. Click **"Save"**

### 2. Create HasRefillsType

1. Click **"+ Add Slot Type"** again
2. Select **"Create custom slot type"**
3. Name: `HasRefillsType`
4. Add two values:

**First value:**

- Value: `yes`
- Synonyms: `yeah, yep, sure, of course, definitely`

**Second value:**

- Value: `no`
- Synonyms: `nope, nah, negative, not really`

5. Click **"Save"**

### 3. Update SetupSlotIntent Slots

Go to your **SetupSlotIntent** and update the slot types:

**prescriptionName slot:**

- Change type from `AMAZON.SearchQuery` or `AMAZON.MedicationName`
- To: `PrescriptionNameType`

**hasRefills slot:**

- Change type from `AMAZON.YesNo`
- To: `HasRefillsType`

### 4. Build Model

Click **"Build Model"** and wait 30-60 seconds.

---

## Why This Works

- **Custom slot types** can be combined with other slots in utterances
- **Phrase slots** (like AMAZON.SearchQuery) cannot be combined with other slots
- Custom types still allow Alexa to accept values not in the list

---

## Your Sample Utterances (These Will Now Work!)

```
The prescription is {prescriptionName} with {pillCount} pills
{prescriptionName} has {pillCount} pills and {hasRefills} refills
Set up {prescriptionName}
{prescriptionName} with {pillCount} pills
I have {prescriptionName}
{prescriptionName} {pillCount} pills {hasRefills} refills
Add {prescriptionName}
Configure {prescriptionName}
My prescription is {prescriptionName}
It's {prescriptionName} with {pillCount} pills
{prescriptionName} bottle has {pillCount} pills
```

All of these will work once you use custom slot types!

---

## Testing

After building, test with:

- "open pillbuddy"
- "the prescription is aspirin with 30 pills"
- When asked about refills, say: "yes"

The skill should now work perfectly! 🎉
