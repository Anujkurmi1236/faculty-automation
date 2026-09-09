import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { formatAttendance } from '../utils/attendance';

const API_URL = 'http://localhost:5000/api';

function LetterGenerator({ selectedStudent, onGenerate }) {
  const [student, setStudent] = useState(selectedStudent || null);
  const [rollNo, setRollNo] = useState('');
  const [generating, setGenerating] = useState(false);
  const [generatedLetter, setGeneratedLetter] = useState(null);

  useEffect(() => {
    if (selectedStudent) {
      setStudent(selectedStudent);
      setRollNo(selectedStudent.rollNo);
    }
  }, [selectedStudent]);

  const fetchStudent = async () => {
    if (!rollNo) return;
    try {
      const response = await axios.get(`${API_URL}/students/${rollNo}`);
      setStudent(response.data);
    } catch (error) {
      alert('Student not found: ' + error.response?.data?.error || error.message);
      setStudent(null);
    }
  };

  const generateLetter = async () => {
    if (!student) return;
    setGenerating(true);
    try {
      const response = await axios.post(`${API_URL}/letters/generate/${student.rollNo}`);
      setGeneratedLetter(response.data);
      if (onGenerate) onGenerate(response.data);
    } catch (error) {
      alert('Error generating letter: ' + error.response?.data?.error || error.message);
    } finally {
      setGenerating(false);
    }
  };

  if (generatedLetter) {
    return (
      <div className="card">
        <h2>Letter Generated Successfully</h2>
        <p>Letter Number: {generatedLetter.letterNumber}</p>
        <div style={{ marginTop: '15px' }}>
          <button onClick={() => window.print()}>Print</button>
          <button 
            className="secondary" 
            onClick={() => {
              setGeneratedLetter(null);
              setStudent(null);
              setRollNo('');
            }}
            style={{ marginLeft: '10px' }}
          >
            Generate Another
          </button>
        </div>
        <div className="letter-container" style={{ marginTop: '20px' }}>
          <LetterViewContent letter={generatedLetter} student={student} />
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>Generate Defaulter Letter</h2>
      
      <div className="form-row">
        <div className="form-group">
          <label>Enter Roll No</label>
          <input 
            type="text" 
            value={rollNo} 
            onChange={(e) => setRollNo(e.target.value)} 
            placeholder="e.g., 001"
          />
        </div>
        <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
          <button onClick={fetchStudent}>Search Student</button>
        </div>
      </div>

      {student && (
        <div style={{ marginTop: '20px' }}>
          <h3>Student Details</h3>
          <table>
            <tbody>
              <tr><td><strong>Name:</strong></td><td>{student.name}</td></tr>
              <tr><td><strong>Roll No:</strong></td><td>{student.rollNo}</td></tr>
              <tr><td><strong>Class:</strong></td><td>{student.class} - Div {student.division}</td></tr>
            </tbody>
          </table>

          <h3>Attendance</h3>
          <div className="attendance-grid">
            <div>
              <h4>Theory</h4>
              <table>
                <thead>
                  <tr><th>Subject</th><th>Lectures</th><th>Present</th><th>Attendance</th></tr>
                </thead>
                <tbody>
                  <tr><td>T1 (DOE)</td><td>{student.theoryAttendance.T1.lectures}</td><td>{student.theoryAttendance.T1.present}</td><td>{formatAttendance(student.theoryAttendance.T1)}</td></tr>
                  <tr><td>T2 (LSCM)</td><td>{student.theoryAttendance.T2.lectures}</td><td>{student.theoryAttendance.T2.present}</td><td>{formatAttendance(student.theoryAttendance.T2)}</td></tr>
                  <tr><td>T3 (PPE)</td><td>{student.theoryAttendance.T3.lectures}</td><td>{student.theoryAttendance.T3.present}</td><td>{formatAttendance(student.theoryAttendance.T3)}</td></tr>
                  <tr><td>T4 (AIML)</td><td>{student.theoryAttendance.T4.lectures}</td><td>{student.theoryAttendance.T4.present}</td><td>{formatAttendance(student.theoryAttendance.T4)}</td></tr>
                </tbody>
              </table>
            </div>
            <div>
              <h4>Practical</h4>
              <table>
                <thead>
                  <tr><th>Subject</th><th>Lectures</th><th>Present</th><th>Attendance</th></tr>
                </thead>
                <tbody>
                  <tr><td>P1 (DOE)</td><td>{student.practicalAttendance.P1.lectures}</td><td>{student.practicalAttendance.P1.present}</td><td>{formatAttendance(student.practicalAttendance.P1)}</td></tr>
                  <tr><td>P2 (PPE)</td><td>{student.practicalAttendance.P2.lectures}</td><td>{student.practicalAttendance.P2.present}</td><td>{formatAttendance(student.practicalAttendance.P2)}</td></tr>
                </tbody>
              </table>
            </div>
          </div>

          <button onClick={generateLetter} disabled={generating} style={{ marginTop: '15px' }}>
            {generating ? 'Generating...' : 'Generate Letter'}
          </button>
        </div>
      )}
    </div>
  );
}

function LetterViewContent({ letter, student }) {
  const date = new Date(letter.date).toLocaleDateString('en-GB', {
    day: '2-digit', month: '2-digit', year: 'numeric'
  });

  return (
    <div>
      <div className="letter-header">
        <div><strong>AF 55</strong></div>
        <div>Date: {date}</div>
      </div>

      <div style={{ marginBottom: '15px' }}>
        <p><strong>To,</strong></p>
        <p>{student.name}</p>
        <p>Class: {student.class} Div: {student.division} Roll No: {student.rollNo}</p>
      </div>

      <div style={{ marginBottom: '15px' }}>
        <p><strong>Subject:</strong> {letter.subject}</p>
        <p><strong>From:</strong> {letter.from}</p>
      </div>

      <div className="letter-body">
        <p><strong>Respected Parent/Guardian,</strong></p>
        <p>
          This is to inform you that the attendance of your ward {student.name} is below the minimum
          requirement as per the norms and regulations of the University of Mumbai for granting the term.
        </p>
        <p>
          You are hereby requested to meet the Class In-Charge and Head of the Department, in person within
          <strong> one week </strong> from the receipt of this letter.
        </p>
        <p>
          Please note that <strong>failure to meet the minimum attendance criteria</strong> as stipulated by
          the University of Mumbai may result in <strong>non-granting of the term for the Academic year</strong>.
        </p>
        <p>
          We sincerely urge all teachers, parents/guardians to work together in the best interest of your
          ward to ensure their academic progress and overall development.
        </p>
        <p>Thank you for your cooperation.</p>
      </div>

      <div style={{ marginTop: '20px' }}>
        <p>Attendance of your ward is as follows:</p>
        
        <div className="letter-table">
          <table>
            <thead>
              <tr>
                <th>Sr. No.</th>
                <th>Roll No</th>
                <th>Student Name</th>
                <th colSpan="4">Theory Attendance (%)</th>
                <th colSpan="2">Practical Attendance (%)</th>
              </tr>
              <tr>
                <th></th>
                <th></th>
                <th></th>
                <th>T1</th>
                <th>T2</th>
                <th>T3</th>
                <th>T4</th>
                <th>P1</th>
                <th>P2</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>1</td>
                <td>{student.rollNo}</td>
                <td>{student.name}</td>
                <td>{formatAttendance(student.theoryAttendance.T1)}</td>
                <td>{formatAttendance(student.theoryAttendance.T2)}</td>
                <td>{formatAttendance(student.theoryAttendance.T3)}</td>
                <td>{formatAttendance(student.theoryAttendance.T4)}</td>
                <td>{formatAttendance(student.practicalAttendance.P1)}</td>
                <td>{formatAttendance(student.practicalAttendance.P2)}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="abbreviation-table">
          <table>
            <thead>
              <tr><th>Abbreviation</th><th>Name of Subject</th><th>Abbreviation</th><th>Name of Subject</th></tr>
            </thead>
            <tbody>
              <tr><td>T1</td><td>Design of Experiments(DOE)</td><td>P1</td><td>DOE</td></tr>
              <tr><td>T2</td><td>Logistics and Supply Chain Management(LSCM)</td><td>P2</td><td>PPE</td></tr>
              <tr><td>T3</td><td>Power Plant Engineering(PPE)</td><td></td><td></td></tr>
              <tr><td>T4</td><td>AIML</td><td></td><td></td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <p style={{ marginTop: '20px' }}>Thanking you.</p>

      <div className="signature-block">
        <div>
          <p>_________</p>
          <p>Class Advisor</p>
          <p>(BE/Mechanical/Div.A)</p>
        </div>
        <div>
          <p>_________</p>
          <p>HoD, Mechanical Engineering</p>
        </div>
        <div>
          <p>_________</p>
          <p>Principal</p>
        </div>
      </div>

      <div style={{ marginTop: '30px', fontSize: '12px' }}>
        <p><strong>Copy to --</strong></p>
        <p>1. Concerned Student</p>
        <p>2. Class In-charge File (Signed copy by Parents has to be returned to Class Advisor)</p>
      </div>
    </div>
  );
}

export default LetterGenerator;