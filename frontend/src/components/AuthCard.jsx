import { motion } from "framer-motion";

export default function AuthCard({ children, className = "" }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`bg-white rounded-2xl shadow-xl p-8 w-full ${className}`}
    >
      {children}
    </motion.div>
  );
}
