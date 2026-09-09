import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import connectDB from './config/database.js';
import studentRoutes from './routes/student.js';
import letterRoutes from './routes/letter.js';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

connectDB();

app.use(cors());
app.use(express.json());

app.use('/api/students', studentRoutes);
app.use('/api/letters', letterRoutes);

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
