const Submission = require('../models/submission.model.js');
const redisClient = require('../config/redis.config.js');

const submitProblem = async (req, res) => {
    try {
        // const { userId, problemId, code, language, action } = req.body;
        let problemId = 2;
        let code = 'print("Hello World")';
        let language = 'python';
        let action = 'SUBMIT';

        // Save submission to database only for SUBMIT action
        let userId = 123;
        let submission;
        if (action === 'SUBMIT') {
            submission = await Submission.create({
                problem_id: problemId,
                code,
                language,
                status: 'Pending',
            });
        }

        // Add submission to Redis queue
        const submissionData = {
            userId,
            problemId,
            code,
            language,
            action,
            submissionId: submission ? submission.submission_id : null,
        };

        await redisClient.lpush('submissionQueue', JSON.stringify(submissionData), (err, result) => {
            if (err) {
                console.error('Error storing data in Redis: ', err);
            } else {
                console.log('Data stored in Redis: ', result);
            }
        });

        res.status(200).json({ message: 'Submission received', submissionId: submission ? submission.id : null });
    } catch (error) {
        console.log("Error submitting the code: ", error);
        res.status(500).json({ error: 'Failed to submit code' });
    }
}

module.exports = { submitProblem }; 