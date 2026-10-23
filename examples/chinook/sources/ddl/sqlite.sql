-- Chinook schema, written by hand for FactModel from the public schema description
-- (eleven tables). Dialect: sqlite. Schema only: rows are synthetic (seed/seed.py).

CREATE TABLE "Artist" (
  "ArtistId" INTEGER NOT NULL,
  "Name" NVARCHAR(120),
  CONSTRAINT "PK_Artist" PRIMARY KEY ("ArtistId")
);

CREATE TABLE "Album" (
  "AlbumId" INTEGER NOT NULL,
  "Title" NVARCHAR(160) NOT NULL,
  "ArtistId" INTEGER NOT NULL,
  CONSTRAINT "PK_Album" PRIMARY KEY ("AlbumId"),
  CONSTRAINT "FK_AlbumArtistId" FOREIGN KEY ("ArtistId") REFERENCES "Artist" ("ArtistId")
);

CREATE TABLE "Genre" (
  "GenreId" INTEGER NOT NULL,
  "Name" NVARCHAR(120),
  CONSTRAINT "PK_Genre" PRIMARY KEY ("GenreId")
);

CREATE TABLE "MediaType" (
  "MediaTypeId" INTEGER NOT NULL,
  "Name" NVARCHAR(120),
  CONSTRAINT "PK_MediaType" PRIMARY KEY ("MediaTypeId")
);

CREATE TABLE "Track" (
  "TrackId" INTEGER NOT NULL,
  "Name" NVARCHAR(200) NOT NULL,
  "AlbumId" INTEGER,
  "MediaTypeId" INTEGER NOT NULL,
  "GenreId" INTEGER,
  "Composer" NVARCHAR(220),
  "Milliseconds" INTEGER NOT NULL,
  "Bytes" INTEGER,
  "UnitPrice" NUMERIC(10,2) NOT NULL,
  CONSTRAINT "PK_Track" PRIMARY KEY ("TrackId"),
  CONSTRAINT "FK_TrackAlbumId" FOREIGN KEY ("AlbumId") REFERENCES "Album" ("AlbumId"),
  CONSTRAINT "FK_TrackGenreId" FOREIGN KEY ("GenreId") REFERENCES "Genre" ("GenreId"),
  CONSTRAINT "FK_TrackMediaTypeId" FOREIGN KEY ("MediaTypeId") REFERENCES "MediaType" ("MediaTypeId")
);

CREATE TABLE "Playlist" (
  "PlaylistId" INTEGER NOT NULL,
  "Name" NVARCHAR(120),
  CONSTRAINT "PK_Playlist" PRIMARY KEY ("PlaylistId")
);

CREATE TABLE "PlaylistTrack" (
  "PlaylistId" INTEGER NOT NULL,
  "TrackId" INTEGER NOT NULL,
  CONSTRAINT "PK_PlaylistTrack" PRIMARY KEY ("PlaylistId", "TrackId"),
  CONSTRAINT "FK_PlaylistTrackPlaylistId" FOREIGN KEY ("PlaylistId") REFERENCES "Playlist" ("PlaylistId"),
  CONSTRAINT "FK_PlaylistTrackTrackId" FOREIGN KEY ("TrackId") REFERENCES "Track" ("TrackId")
);

CREATE TABLE "Employee" (
  "EmployeeId" INTEGER NOT NULL,
  "LastName" NVARCHAR(20) NOT NULL,
  "FirstName" NVARCHAR(20) NOT NULL,
  "Title" NVARCHAR(30),
  "ReportsTo" INTEGER,
  "BirthDate" DATETIME,
  "HireDate" DATETIME,
  "Address" NVARCHAR(70),
  "City" NVARCHAR(40),
  "State" NVARCHAR(40),
  "Country" NVARCHAR(40),
  "PostalCode" NVARCHAR(10),
  "Phone" NVARCHAR(24),
  "Fax" NVARCHAR(24),
  "Email" NVARCHAR(60),
  CONSTRAINT "PK_Employee" PRIMARY KEY ("EmployeeId"),
  CONSTRAINT "FK_EmployeeReportsTo" FOREIGN KEY ("ReportsTo") REFERENCES "Employee" ("EmployeeId")
);

CREATE TABLE "Customer" (
  "CustomerId" INTEGER NOT NULL,
  "FirstName" NVARCHAR(40) NOT NULL,
  "LastName" NVARCHAR(20) NOT NULL,
  "Company" NVARCHAR(80),
  "Address" NVARCHAR(70),
  "City" NVARCHAR(40),
  "State" NVARCHAR(40),
  "Country" NVARCHAR(40),
  "PostalCode" NVARCHAR(10),
  "Phone" NVARCHAR(24),
  "Fax" NVARCHAR(24),
  "Email" NVARCHAR(60) NOT NULL,
  "SupportRepId" INTEGER,
  CONSTRAINT "PK_Customer" PRIMARY KEY ("CustomerId"),
  CONSTRAINT "FK_CustomerSupportRepId" FOREIGN KEY ("SupportRepId") REFERENCES "Employee" ("EmployeeId")
);

CREATE TABLE "Invoice" (
  "InvoiceId" INTEGER NOT NULL,
  "CustomerId" INTEGER NOT NULL,
  "InvoiceDate" DATETIME NOT NULL,
  "BillingAddress" NVARCHAR(70),
  "BillingCity" NVARCHAR(40),
  "BillingState" NVARCHAR(40),
  "BillingCountry" NVARCHAR(40),
  "BillingPostalCode" NVARCHAR(10),
  "Total" NUMERIC(10,2) NOT NULL,
  CONSTRAINT "PK_Invoice" PRIMARY KEY ("InvoiceId"),
  CONSTRAINT "FK_InvoiceCustomerId" FOREIGN KEY ("CustomerId") REFERENCES "Customer" ("CustomerId")
);

CREATE TABLE "InvoiceLine" (
  "InvoiceLineId" INTEGER NOT NULL,
  "InvoiceId" INTEGER NOT NULL,
  "TrackId" INTEGER NOT NULL,
  "UnitPrice" NUMERIC(10,2) NOT NULL,
  "Quantity" INTEGER NOT NULL,
  CONSTRAINT "PK_InvoiceLine" PRIMARY KEY ("InvoiceLineId"),
  CONSTRAINT "FK_InvoiceLineInvoiceId" FOREIGN KEY ("InvoiceId") REFERENCES "Invoice" ("InvoiceId"),
  CONSTRAINT "FK_InvoiceLineTrackId" FOREIGN KEY ("TrackId") REFERENCES "Track" ("TrackId")
);
