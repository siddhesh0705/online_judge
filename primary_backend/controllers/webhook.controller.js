const Submission = require('../models/submission.model');


const handleWebhook = async(req, res) => {
    console.log('Received webhook:', req.body);
    const { submission_id, problem_id, user_id, results, status } = req.body;

    try {
        // Find the submission entry in the database
        const submission = await Submission.findByPk(submission_id);
        console.log(`Submission ${submission_id} found in the database`);

        if (!submission) {
            return res.status(404).json({ error: 'Submission not found' });
        }


        // Update the database entry
        await Submission.update(
            { status, results, updatedAt: new Date() },
            { where: { submission_id: submission_id } }
        );

        console.log(`Submission ${submission_id} updated with status: ${status}, output: ${results}`);

        // Respond to FastAPI that the webhook was received successfully
        res.status(200).json({ message: 'Webhook processed and database updated successfully.' });
    }
    catch(error) {
        console.error('Error processing webhook:', error);
        res.status(500).json({ error: 'Failed to process webhook.' });
    }
};

module.exports = { handleWebhook };
