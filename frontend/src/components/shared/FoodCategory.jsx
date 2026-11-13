import { useState } from "react";

function FoodCategory() {
  const [category, setCategory] = useState("");

  return (
    <div>
      <h3>Who is this food for?</h3>

      <label>
        <input
          type="radio"
          name="foodCategory"
          value="human"
          checked={category === "human"}
          onChange={(e) => setCategory(e.target.value)}
        />
        Human
      </label>

      <br />

      <label>
        <input
          type="radio"
          name="foodCategory"
          value="animal"
          checked={category === "animal"}
          onChange={(e) => setCategory(e.target.value)}
        />
        Animal
      </label>

      <p>Selected category: {category || "None"}</p>
    </div>
  );
}

export default FoodCategory;