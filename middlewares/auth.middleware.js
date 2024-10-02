const jwt = require('jsonwebtoken');
require('dotenv').config();

const authMiddleware = (req, res, next) => {
    const token = req.cookies.token;

    if(!token) {
        return res.status(401).json({ message : 'Not Login Yet' });
    }

    try {
        const verifyToken = jwt.verify(token, process.env.JWT_SECRET);
        req.user = verifyToken;
        next();
    }
    catch (error) {
        res.status(403).json({ message : 'Invalid token' })
    }
};


module.exports = {
    authMiddleware
};