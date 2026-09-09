import mongoose from 'mongoose';

const studentSchema = new mongoose.Schema({
  rollNo: { type: String, required: true, unique: true },
  name: { type: String, required: true },
  class: { type: String, required: true },
  division: { type: String, required: true },
  theoryAttendance: {
    T1: { lectures: { type: Number, default: 0, min: 0 }, present: { type: Number, default: 0, min: 0 } },
    T2: { lectures: { type: Number, default: 0, min: 0 }, present: { type: Number, default: 0, min: 0 } },
    T3: { lectures: { type: Number, default: 0, min: 0 }, present: { type: Number, default: 0, min: 0 } },
    T4: { lectures: { type: Number, default: 0, min: 0 }, present: { type: Number, default: 0, min: 0 } }
  },
  practicalAttendance: {
    P1: { lectures: { type: Number, default: 0, min: 0 }, present: { type: Number, default: 0, min: 0 } },
    P2: { lectures: { type: Number, default: 0, min: 0 }, present: { type: Number, default: 0, min: 0 } }
  },
  createdAt: { type: Date, default: Date.now }
});

export default mongoose.model('Student', studentSchema);