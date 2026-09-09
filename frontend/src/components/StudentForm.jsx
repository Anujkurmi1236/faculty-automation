import React, { useState } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:5000/api';

function StudentForm({ onSuccess }) {
  const [student, setStudent] = useState({
    rollNo: '',
    name: '',
    class: 'BE',
    division: 'A',
    theoryAttendance: {
      T1: { lectures: 0, present: 0 }, T2: { lectures: 0, present: 0 },
      T3: { lectures: 0, present: 0 }, T4: { lectures: 0, present: 0 }
    },
    practicalAttendance: {
      P1: { lectures: 0, present: 0 }, P2: { lectures: 0, present: 0 }
    }
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    if (name.startsWith('theory_')) {
      const [, key, field] = name.split('_');
      setStudent({
        ...student,
        theoryAttendance: {
          ...student.theoryAttendance,
          [key]: { ...student.theoryAttendance[key], [field]: parseInt(value, 10) || 0 }
        }
      });
    } else if (name.startsWith('practical_')) {
      const [, key, field] = name.split('_');
      setStudent({
        ...student,
        practicalAttendance: {
          ...student.practicalAttendance,
          [key]: { ...student.practicalAttendance[key], [field]: parseInt(value, 10) || 0 }
        }
      });
    } else {
      setStudent({ ...student, [name]: value });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/students`, student);
      onSuccess();
    } catch (error) {
      alert('Error adding student: ' + error.response?.data?.error || error.message);
    }
  };

  return (
    <div className="card">
      <h2>Add New Student</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <div className="form-group">
            <label>Roll No</label>
            <input type="text" name="rollNo" value={student.rollNo} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label>Name</label>
            <input type="text" name="name" value={student.name} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label>Class</label>
            <input type="text" name="class" value={student.class} onChange={handleChange} />
          </div>
          <div className="form-group">
            <label>Division</label>
            <input type="text" name="division" value={student.division} onChange={handleChange} />
          </div>
        </div>

        <h3>Theory Attendance (Lectures / Present)</h3>
        <div className="form-row">
          {[['T1', 'T1 - DOE'], ['T2', 'T2 - LSCM'], ['T3', 'T3 - PPE'], ['T4', 'T4 - AIML']].map(([key, label]) => (
            <div className="form-group" key={key}>
              <label>{label}</label>
              <input type="number" name={`theory_${key}_lectures`} value={student.theoryAttendance[key].lectures} onChange={handleChange} min="0" placeholder="Lectures" />
              <input type="number" name={`theory_${key}_present`} value={student.theoryAttendance[key].present} onChange={handleChange} min="0" max={student.theoryAttendance[key].lectures} placeholder="Present" />
            </div>
          ))}
        </div>

        <h3>Practical Attendance (Lectures / Present)</h3>
        <div className="form-row">
          {[['P1', 'P1 - DOE'], ['P2', 'P2 - PPE']].map(([key, label]) => (
            <div className="form-group" key={key}>
              <label>{label}</label>
              <input type="number" name={`practical_${key}_lectures`} value={student.practicalAttendance[key].lectures} onChange={handleChange} min="0" placeholder="Lectures" />
              <input type="number" name={`practical_${key}_present`} value={student.practicalAttendance[key].present} onChange={handleChange} min="0" max={student.practicalAttendance[key].lectures} placeholder="Present" />
            </div>
          ))}
        </div>

        <button type="submit">Add Student</button>
      </form>
    </div>
  );
}

export default StudentForm;