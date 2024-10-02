const { Submission } = require('../models/submission.model');


const handleWebhook = async(req, res) => {
    const { status, output, submissionId } = req.body;

    try {
        // Find the submission entry in the database
        const submission = await Submission.findByPk(submissionId);

        if (!submission) {
            return res.status(404).json({ error: 'Submission not found' });
        }

        // Update the database entry
        await Submission.update(
            { status, output, updatedAt: new Date() },
            { where: { submission_id: submissionId } }
        );

        console.log(`Submission ${submissionId} updated with status: ${status}, output: ${output}`);

        // Respond to FastAPI that the webhook was received successfully
        res.status(200).json({ message: 'Webhook processed and database updated successfully.' });
    }
    catch(error) {
        console.error('Error processing webhook:', error);
        res.status(500).json({ error: 'Failed to process webhook.' });
    }
};

module.exports = { handleWebhook };
