import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { formatAttendance } from '../utils/attendance';

const API_URL = 'http://localhost:5000/api';

function LetterView() {
  const [letters, setLetters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedLetter, setSelectedLetter] = useState(null);

  useEffect(() => {
    fetchLetters();
  }, []);

  const fetchLetters = async () => {
    try {
      const response = await axios.get(`${API_URL}/letters`);
      setLetters(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching letters:', error);
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div className="card">
      <h2>Generated Letters</h2>
      {letters.length === 0 ? (
        <p>No letters generated yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Letter No.</th>
              <th>Student</th>
              <th>Roll No</th>
              <th>Date</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {letters.map((letter) => (
              <tr key={letter._id}>
                <td>{letter.letterNumber}</td>
                <td>{letter.studentId?.name || 'N/A'}</td>
                <td>{letter.studentId?.rollNo || 'N/A'}</td>
                <td>{new Date(letter.generatedAt).toLocaleDateString()}</td>
                <td>
                  <button onClick={() => setSelectedLetter(selectedLetter === letter._id ? null : letter._id)}>
                    {selectedLetter === letter._id ? 'Hide' : 'View'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selectedLetter && (
        <div style={{ marginTop: '20px' }}>
          <h3>Letter Details</h3>
          <div className="letter-container">
            <LetterContent letterId={selectedLetter} />
          </div>
        </div>
      )}
    </div>
  );
}

function LetterContent({ letterId }) {
  const [letter, setLetter] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLetter = async () => {
      try {
        const response = await axios.get(`${API_URL}/letters/${letterId}`);
        setLetter(response.data);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching letter:', error);
        setLoading(false);
      }
    };
    fetchLetter();
  }, [letterId]);

  if (loading) return <div>Loading letter details...</div>;
  if (!letter) return <div>Letter not found.</div>;

  const student = letter.studentId;
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

export default LetterView;